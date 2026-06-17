const { setSocket, getSocket } = require("./session_manager")

const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    normalizeMessageContent,
    downloadContentFromMessage
} = require("baileys")

const P = require("pino")
const fs = require("fs")
const path = require("path")
const os = require("os")

function writeEvent(event, data) {
    process.stdout.write(JSON.stringify({ event, data }) + "\n")
}

function extractPhone(jid) {
    if (!jid) return ""
    return jid.split("@")[0]
}

function extFromMime(mime) {
    if (!mime) return "bin"
    const subtype = mime.split("/")[1]?.split(";")[0]
    if (!subtype) return "bin"
    switch (subtype) {
        case "jpeg":
        case "x-jpeg":
            return "jpg"
        case "png":
            return "png"
        case "webp":
            return "webp"
        case "mp4":
        case "mp4v":
            return "mp4"
        case "ogg":
        case "opus":
            return "ogg"
        case "mpeg":
            return "mp3"
        case "pdf":
            return "pdf"
        case "vnd.openxmlformats-officedocument.wordprocessingml.document":
            return "docx"
        default:
            return subtype.replace(/[^a-z0-9]/gi, "") || "bin"
    }
}

const AUTH_DIR = path.join(os.homedir(), ".pywacli", "auth")

function clearAuthState() {
    try {
        fs.rmSync(AUTH_DIR, { recursive: true, force: true })
        console.error("Cleared auth state")
    } catch (err) {
        console.error("Failed to clear auth state:", err)
    }
}

async function startSock() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)

    const sock = makeWASocket({
        auth: state,
        logger: P({ level: "silent" }),
        markOnlineOnConnect: false,
        browser: ["PyWacli", "Chrome", "1.0.0"]
    })

    setSocket(sock)

    sock.ev.on("connection.update", async (update) => {
        const { connection, lastDisconnect, qr } = update

        if (qr) {
            console.error("\nScan QR:\n")
            writeEvent("auth.qr", { qr })
        }

        if (connection === "open") {
            console.error("Connected")
            writeEvent("connection.open", { user: sock.user })
        }

        if (connection === "close") {
            const statusCode = lastDisconnect?.error?.output?.statusCode
            const loggedOut = statusCode === DisconnectReason.loggedOut
            const replaced = statusCode === DisconnectReason.connectionReplaced

            writeEvent("connection.close", { reason: statusCode, loggedOut })
            console.error("Disconnected")

            if (loggedOut) {
                console.error("Logged out - clearing session and showing a new QR...")
                clearAuthState()
                setTimeout(() => startSock(), 3000)
            } else if (replaced) {
                // Another session/device took over this account. Reconnecting
                // here would fight it and cause a connect/disconnect storm, so
                // stop and let the user resolve the conflict.
                console.error("Connection replaced by another session. Not reconnecting.")
                console.error("Close other WhatsApp Web/device sessions (and any stray node), then restart Connect.")
                writeEvent("error", { message: "Connection replaced by another session" })
            } else {
                console.error("Reconnecting...")
                setTimeout(() => startSock(), 3000)
            }
        }
    })

    sock.ev.on("creds.update", saveCreds)

    sock.ev.on("messages.upsert", async ({ messages }) => {
        console.error("\n========= MESSAGE UPSERT =========")

        try {
            for (const msg of messages) {
                try {
                    const isFromMe = msg.key.fromMe
                    const contactJid = msg.key.remoteJid
                    const senderJid = isFromMe
                        ? sock.user.id
                        : (msg.key.participant || msg.key.remoteJid)
                    const phoneNumber = extractPhone(senderJid)
                    const contactPhone = extractPhone(contactJid)
                    const pushName = msg.pushName || ""

                    const msgContent = normalizeMessageContent(msg.message)
                    if (!msgContent) continue

                    const viewOnceMsg = msgContent.viewOnceMessage?.message
                    const viewOnceMsgV2 = msgContent.viewOnceMessageV2?.message
                    const viewOnceMsgV2Ext = msgContent.viewOnceMessageV2Extension?.message
                    const isViewOnce = !!(viewOnceMsg || viewOnceMsgV2 || viewOnceMsgV2Ext)

                    let mediaMessage = null
                    let mediaType = null

                    if (viewOnceMsg) {
                        const type = Object.keys(viewOnceMsg)[0]
                        mediaType = type.replace('Message', '').toLowerCase()
                        mediaMessage = viewOnceMsg[type]
                    } else if (viewOnceMsgV2) {
                        const type = Object.keys(viewOnceMsgV2)[0]
                        mediaType = type.replace('Message', '').toLowerCase()
                        mediaMessage = viewOnceMsgV2[type]
                    } else if (viewOnceMsgV2Ext) {
                        const type = Object.keys(viewOnceMsgV2Ext)[0]
                        mediaType = type.replace('Message', '').toLowerCase()
                        mediaMessage = viewOnceMsgV2Ext[type]
                    } else {
                        const image = msgContent?.imageMessage
                        const video = msgContent?.videoMessage
                        const audio = msgContent?.audioMessage
                        const document = msgContent?.documentMessage
                        if (image) { mediaType = "image"; mediaMessage = image }
                        else if (video) { mediaType = "video"; mediaMessage = video }
                        else if (audio) { mediaType = "audio"; mediaMessage = audio }
                        else if (document) { mediaType = "document"; mediaMessage = document }
                    }

                    const isStatus = msg.key.remoteJid === "status@broadcast"

                    console.error("Sender:", msg.key.remoteJid)
                    console.error("Phone:", phoneNumber)
                    console.error("PushName:", pushName)
                    console.error("Message ID:", msg.key.id)
                    console.error("Media Type:", mediaType || "none")
                    if (isViewOnce) console.error("View-once media")

                    if (mediaMessage && mediaType) {
                        const stream = await downloadContentFromMessage(mediaMessage, mediaType)
                        let buffer = Buffer.from([])
                        for await (const chunk of stream) {
                            buffer = Buffer.concat([buffer, chunk])
                        }

                        const mimeType = mediaMessage?.mimetype
                        const extension = extFromMime(mimeType)
                        const fileName = `${msg.key.id}.${extension}`
                        const contactDir = `${pushName}_${contactPhone}`
                        const mediaPlural = `${mediaType}s`
                        const folder = isViewOnce
                            ? `media/viewonce/${contactDir}`
                            : `media/${mediaPlural}/${contactDir}`

                        fs.mkdirSync(folder, { recursive: true })
                        const filePath = path.join(folder, fileName)
                        fs.writeFileSync(filePath, buffer)

                        writeEvent("media.new", {
                            jid: msg.key.remoteJid,
                            id: msg.key.id,
                            fileName,
                            filePath,
                            mimeType,
                            mediaType,
                            isStatus,
                            isViewOnce,
                            pushName,
                            phoneNumber,
                            contactPhone,
                            fromMe: msg.key.fromMe,
                            participant: msg.key.participant,
                            timestamp: Date.now()
                        })

                        writeEvent("conversation.new", {
                            id: msg.key.id,
                            jid: msg.key.remoteJid,
                            messageType: "media",
                            text: mediaMessage?.caption || "",
                            mediaType,
                            mimeType,
                            fileName,
                            filePath,
                            pushName,
                            phoneNumber,
                            contactPhone,
                            fromMe: msg.key.fromMe,
                            participant: msg.key.participant,
                            isStatus,
                            isViewOnce,
                            timestamp: Date.now()
                        })

                        console.error("Media downloaded:", filePath)
                        console.error(`Downloaded view once ${mediaType} of size ${buffer.length}`)
                    }

                    if (!msg.message) continue

                    const jid = msg.key.remoteJid
                    const text =
                        msg.message.conversation ||
                        msg.message.extendedTextMessage?.text ||
                        msg.message.imageMessage?.caption ||
                        msg.message.videoMessage?.caption

                    if (!text) continue

                    const payload = {
                        jid,
                        text,
                        id: msg.key.id,
                        pushName,
                        phoneNumber,
                        contactPhone,
                        fromMe: msg.key.fromMe,
                        participant: msg.key.participant,
                        timestamp: Date.now()
                    }

                    writeEvent("conversation.new", {
                        ...payload,
                        messageType: "text",
                        mediaType: null,
                        mimeType: null,
                        fileName: null,
                        filePath: null,
                        isStatus
                    })

                    if (isStatus) {
                        payload.isMyStatus = msg.key.participant === sock.user.id
                        writeEvent("status.new", payload)
                        console.error(`STATUS: ${text}`)
                    } else {
                        writeEvent("message.new", payload)
                        console.error(`${jid}: ${text}`)
                    }

                } catch (err) {
                    console.error("Error processing message:", err)
                }
            }
        } catch (err) {
            console.error("messages.upsert error:", err)
        }
    })

    sock.ev.on("messages.update", async (updates) => {
        try {
            for (const update of updates) {
                try {
                    const sender = update.key.remoteJid
                    const edited = update.update?.message?.editedMessage?.message
                    if (!edited) continue

                    const text = edited.conversation || edited.extendedTextMessage?.text

                    console.error("\n========= MESSAGE EDITED =========")
                    console.error("Message Edited")
                    console.error("Sender:", sender)
                    console.error("New Text:", text)

                    writeEvent("message.update", {
                        jid: sender,
                        text,
                        id: update.key.id,
                        pushName: update.pushName,
                        fromMe: update.key.fromMe,
                        timestamp: Date.now()
                    })

                } catch (err) {
                    console.error("Error processing updated message:", err)
                }
            }
        } catch (err) {
            console.error("messages.update error:", err)
        }
    })

    sock.ev.on("messages.delete", (item) => {
        try {
            console.error("========== Message Deleted =========")
            const deletedMessages = item.keys.map((k) => ({
                id: k.id,
                jid: k.remoteJid,
                fromMe: k.fromMe,
                pushName: item.pushName,
                timestamp: Date.now()
            }))

            writeEvent("message.delete", { messages: deletedMessages })

        } catch (err) {
            console.error("messages.delete error:", err)
        }
    })

    sock.ev.on("messages.reaction", (reactions) => {
        try {
            console.error("========== Reaction =========")
            const formattedReactions = reactions.map((r) => ({
                jid: r.key.remoteJid,
                messageId: r.key.id,
                reaction: r.reaction?.text,
                fromMe: r.key.fromMe,
                pushName: r.pushName,
                reactedTo: {
                    id: r.reaction?.key?.id,
                    jid: r.reaction?.key?.remoteJid,
                    fromMe: r.reaction?.key?.fromMe,
                    pushName: r.reaction?.pushName
                },
                timestamp: r.reaction?.senderTimestampMs?.low || Date.now()
            }))

            writeEvent("message.reaction", { reactions: formattedReactions })

        } catch (err) {
            console.error("messages.reaction error:", err)
        }
    })

    sock.ev.on("presence.update", (presence) => {
        try {
            console.error("========== Presence =========")
            writeEvent("presence.update", { presence })
        } catch (err) {
            console.error("presence.update error:", err)
        }
    })
}

// Handle one newline-delimited JSON command. `reply` (if given) sends a JSON
// response back to the caller — used by the TCP server so a separate Send
// process can learn whether the message went out.
async function handleCommand(line, reply) {
    if (!line.trim()) return

    let msg
    try {
        msg = JSON.parse(line)
    } catch (err) {
        console.error("Failed to parse command:", err)
        if (reply) reply({ event: "error", data: { message: "Invalid JSON" } })
        return
    }

    if (msg.event !== "send.message") return

    const sock = getSocket()
    if (!sock) {
        const payload = { event: "error", data: { message: "Socket not initialized" } }
        writeEvent(payload.event, payload.data)
        if (reply) reply(payload)
        return
    }

    try {
        console.error("Sending message to", msg.data.jid)
        await sock.sendMessage(msg.data.jid, { text: msg.data.text })
        console.error("Message Sent to", msg.data.jid)
        const payload = { event: "message.sent", data: { jid: msg.data.jid, text: msg.data.text } }
        writeEvent(payload.event, payload.data)
        if (reply) reply(payload)
    } catch (err) {
        console.error("Failed to send message:", err)
        const payload = { event: "error", data: { message: String((err && err.message) || err) } }
        writeEvent(payload.event, payload.data)
        if (reply) reply(payload)
    }
}

// Commands over stdin (same-process use).
const readline = require("readline")
const rl = readline.createInterface({ input: process.stdin })
rl.on("line", (line) => { handleCommand(line, null) })

// Commands over a local TCP socket so a separate `Send` process (another
// terminal) can reach this single connection without opening its own.
const net = require("net")
const SEND_HOST = process.env.PYWACLI_SEND_HOST || "127.0.0.1"
const SEND_PORT = parseInt(process.env.PYWACLI_SEND_PORT || "8765", 10)

const commandServer = net.createServer((conn) => {
    let buffer = ""
    conn.on("data", (chunk) => {
        buffer += chunk.toString("utf8")
        let idx
        while ((idx = buffer.indexOf("\n")) >= 0) {
            const line = buffer.slice(0, idx)
            buffer = buffer.slice(idx + 1)
            handleCommand(line, (payload) => {
                try { conn.write(JSON.stringify(payload) + "\n") } catch (e) { }
            })
        }
    })
    conn.on("error", () => { })
})

commandServer.on("error", (err) => {
    if (err.code === "EADDRINUSE") {
        // Another Connect already owns the port (and the WhatsApp socket).
        // Exit instead of opening a second socket on the same auth, which
        // would make WhatsApp kick one and trigger a reconnect storm.
        console.error(`Command port ${SEND_HOST}:${SEND_PORT} is in use — another Connect session is already running. Exiting to avoid a duplicate connection.`)
        process.exit(1)
    } else {
        console.error("Command server error:", err)
    }
})

// Only open the WhatsApp socket once we own the command port — this enforces a
// single live connection across terminals.
commandServer.listen(SEND_PORT, SEND_HOST, () => {
    console.error(`Command server listening on ${SEND_HOST}:${SEND_PORT}`)
    startSock()
})
