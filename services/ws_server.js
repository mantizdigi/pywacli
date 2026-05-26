const { text } = require("express")
const WebSocket = require("ws")

const clients = new Set()

const wss = new WebSocket.Server({
    port: 3000
})

wss.on("connection", (ws) => {

    console.log("🟢 Client Connected")

    clients.add(ws)

    // WELCOME
    ws.send(JSON.stringify({
        event: "server.connected",
        data: {
            message: "Welcome to PyWacli"
        }
    }))

    // RECEIVE FROM CLIENT
    ws.on("message", async (message) => {

        try {

            const data = JSON.parse(message)

            console.log("📨 Client Says:", data)

            if (data.event === "send.message"){

                const {
                    getSocket
                } = require("./session_manager")

                const sock = getSocket()

                if (!sock) return 
                console.log("Sending message to", data.data.jid)
                await sock.sendMessage(
                    data.data.jid,
                    {
                        text: data.data.text
                    }
                )
                console.log("✅ Message Sent to", data.data.jid)
            }

        } catch (err) {

            console.log("Invalid JSON", err)
        }
    })

    // DISCONNECT
    ws.on("close", () => {

        console.log("🔴 Client Disconnected")

        clients.delete(ws)
    })
})

function broadcastEvent(event, data) {

    const payload = JSON.stringify({
        event,
        data,
        timestamp: Date.now()
    })

    for (const client of clients) {

        if (client.readyState === WebSocket.OPEN) {
            client.send(payload)
        }
    }
}

module.exports = {
    broadcastEvent
}

console.log("🚀 WS Server running at ws://localhost:3000")