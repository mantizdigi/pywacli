
const {
    broadcastEvent
} = require("./ws_server")

const {
    setSocket
} = require("./session_manager")


const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason
} = require("baileys")

const P = require("pino")
const qrcode = require("qrcode-terminal")

const fs = require("fs")
const path = require("path")
const os = require("os")
const{
    normalizeMessageContent,
    downloadContentFromMessage
} = require("baileys")

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

// Wipe stale credentials so the next startSock() begins a fresh
// pairing and Baileys emits a new QR (used after a logout / when
// the saved session is no longer valid).
function clearAuthState() {

    try {

        fs.rmSync(AUTH_DIR, {
            recursive: true,
            force: true
        })

        console.log("🧹 Cleared auth state")

    } catch (err) {

        console.log("❌ Failed to clear auth state:", err)
    }
}


async function startSock() {

    const {
        state,
        saveCreds
    } = await useMultiFileAuthState(AUTH_DIR)

    const sock = makeWASocket({
        auth: state,
        logger: P({ level: "silent" }),

        markOnlineOnConnect: false,

        browser: ["PyWacli", "Chrome", "1.0.0"]
    })

    setSocket(sock)

    sock.ev.on("connection.update", async (update) => {

        const {
            connection,
            lastDisconnect,
            qr
        } = update

        // QR EVENT
        if (qr) {

            console.log("\nScan QR:\n")

            broadcastEvent("auth.qr", {
                qr
            })

            qrcode.generate(qr, {
                small: true
            })
        }

        // CONNECTED
        if (connection === "open") {

            console.log("✅ Connected")

            broadcastEvent("connection.open", {
                user: sock.user
            })
        }

        // DISCONNECTED
        if (connection === "close") {

            const statusCode =
                lastDisconnect?.error?.output?.statusCode

            const loggedOut =
                statusCode === DisconnectReason.loggedOut

            broadcastEvent("connection.close", {
                reason: statusCode,
                loggedOut
            })

            console.log("❌ Disconnected")

            if (loggedOut) {

                // Session is dead (logged out from the phone).
                // Drop the stale creds and restart so a brand new
                // QR is generated for re-pairing.
                console.log("🚪 Logged out — clearing session and showing a new QR...")

                clearAuthState()

                setTimeout(() => {
                    startSock()
                }, 3000)

            } else {

                console.log("♻️ Reconnecting...")

                setTimeout(() => {
                    startSock()
                }, 3000)
            }
        }
    })

    // SAVE CREDS
    sock.ev.on("creds.update", saveCreds)

    // RECEIVE MESSAGES
    sock.ev.on("messages.upsert", async ({ messages }) => {

        console.log("\n========= MESSAGE UPSERT =========")

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

                    // Determine media message and type
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

                    const isStatus =
                        msg.key.remoteJid === "status@broadcast"

                    console.log("Sender:", msg.key.remoteJid)
                    console.log("Phone:", phoneNumber)
                    console.log("PushName:", pushName)
                    console.log("Message ID:", msg.key.id)
                    console.log("Media Type:", mediaType || "none")
                    if (isViewOnce) console.log("👁 View-once media")

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

                        broadcastEvent("media.new",{
                            jid: msg.key.remoteJid,
                            id:msg.key.id,
                            fileName,
                            filePath,
                            mimeType,
                            mediaType,
                            isStatus,
                            isViewOnce,
                            pushName,
                            phoneNumber,
                            contactPhone,
                            fromMe:msg.key.fromMe,
                            participant:msg.key.participant,
                            timestamp:Date.now()
                        })

                        broadcastEvent("conversation.new", {
                                id: msg.key.id,
                                jid: msg.key.remoteJid,
                                messageType: "media",
                                text:
                                    mediaMessage?.caption ||
                                    "",

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

                        console.log("Media downloaded:", filePath)
                        console.log(`Downloaded view once ${mediaType} of size ${buffer.length}`)
                    }

                    if (!msg.message) continue

                    const jid = msg.key.remoteJid

                    // TEXT EXTRACTION
                    const text =
                        msg.message.conversation ||
                        msg.message.extendedTextMessage?.text ||
                        msg.message.imageMessage?.caption ||
                        msg.message.videoMessage?.caption

                    if (!text) continue

                    // COMMON PAYLOAD
                    const payload = {

                        jid,
                        text,
                        id: msg.key.id,
                        pushName,
                        phoneNumber,
                        contactPhone,
                        fromMe:
                            msg.key.fromMe,
                        participant:
                            msg.key.participant,
                        timestamp:
                            Date.now()
                    }

                    broadcastEvent("conversation.new", {
                        ...payload,
                        messageType: "text",
                        mediaType: null,
                        mimeType: null,
                        fileName: null,
                        filePath: null,
                        isStatus
                    })
                    
                    // STATUS EVENT
                    if (isStatus) {

                        payload.isMyStatus =
                            msg.key.participant === sock.user.id

                        broadcastEvent(
                            "status.new",
                            payload
                        )
                        console.log(
                            `📸 STATUS: ${text}`
                        )
                    }

                    // NORMAL MESSAGE
                    else {
                        broadcastEvent(
                            "message.new",
                            payload
                        )
                        console.log(
                            `📩 ${jid}: ${text}`
                        )
                    }

                } catch (err) {

                    console.log(
                        "❌ Error processing message:",
                        err
                    )
                }
            }

        } catch (err) {

            console.log(
                "❌ messages.upsert error:",
                err
            )
        }
    })


    // MESSAGE UPDATE
    sock.ev.on("messages.update", async (updates) => {

        try {


            for (const update of updates) {

                try {

                    const sender = update.key.remoteJid

                    const edited =
                        update.update?.message?.editedMessage?.message

                    if (!edited) continue

                    const text =
                        edited.conversation ||
                        edited.extendedTextMessage?.text

                    console.log("\n========= MESSAGE EDITED =========")
                    console.log("✏️ Message Edited")
                    console.log("Sender:", sender)
                    console.log("New Text:", text)

                    broadcastEvent("message.update", {
                        jid: sender,
                        text,
                        id: update.key.id,
                        pushName: update.pushName,
                        fromMe: update.key.fromMe,
                        timestamp:Date.now()
                    })

                } catch (err) {

                    console.log("❌ Error processing updated message:", err)
                }
            }

        } catch (err) {

            console.log("❌ messages.update error:", err)
        }
    })


    // MESSAGE DELETE
    sock.ev.on("messages.delete", (item) => {

        try {

            console.log("==========🗑 Message Deleted =========")
        
            const deletedMessages = item.keys.map((k) => ({

                id: k.id,
                jid: k.remoteJid,
                fromMe: k.fromMe,
                pushName: item.pushName,
                timestamp: Date.now()

            }))

            broadcastEvent("message.delete", {
                messages: deletedMessages
            })

        } catch (err) {

            console.log("❌ messages.delete error:", err)
        }
    })


    // MESSAGE REACTION
    sock.ev.on("messages.reaction", (reactions) => {

        try {

            console.log("==========❤️ Reaction =========")

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

                timestamp:
                    r.reaction?.senderTimestampMs?.low ||
                    Date.now()

            }))

            broadcastEvent("message.reaction", {
                reactions: formattedReactions
            })

        } catch (err) {

            console.log("❌ messages.reaction error:", err)
        }
    })


    // PRESENCE UPDATE
    sock.ev.on("presence.update", (presence) => {

        try {

            console.log("==========🟢 Presence =========")
            broadcastEvent("presence.update", {
                presence
            })

        } catch (err) {

            console.log("❌ presence.update error:", err)
        }
    })

}


startSock()