let sock = null

function setSocket(socket) {
    sock = socket
}

function getSocket() {
    return sock
}

module.exports = {
    setSocket,
    getSocket
}