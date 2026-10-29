var socket = io();

messagetextBlock = document.getElementById("message");
messages = document.getElementById("chat-messages");
conversation = JSON.parse(document.getElementById("getConversation").textContent).conversation_id;
user_id = JSON.parse(document.getElementById("getConversation").textContent).user_id;

if (conversation !== null) {
    socket.on("connect", function (event) {
        socket.emit("join_conversation", {
            conversation_id: conversation
        }, function (response) {
            if (response && response.error) {
                console.log("Error");
            } else {
                console.log("Connected");
            }
        }
        )
    })
} else {
    console.log("No convo")
}

document.getElementById("message").addEventListener("keyup", function (event) {
    if (event.key == "Enter") {
        event.preventDefault();
        let message = document.getElementById("message").value.trim();
        
        if (!message || conversation === null) {
            console.log("No conversations")
        } else {
            socket.emit("new_message", {
                conversation_id: conversation,
                message: message
            }, function (response) {
                    if (response && response.error) {
                        console.log("send fail");
                    } 
                }
            );

            messagetextBlock.value = "";
        }
    }
});

socket.on("chat", function (data) {

    if (Number(data.conversation_id) !== Number(conversation)) {
        console.log("Error")
    } else {

        let li = document.createElement("li");

        if (Number(data.sender_id) === Number(user_id)) {
            sender = "You"
            li.classList.add("message-own");
        } else {
            sender = (data.username || "Anonymous User")
            li.classList.add("message-incoming");
        }

        li.classList.add("message-bubble");
        let senderLabel = document.createElement("strong");
        senderLabel.classList.add("message-sender");
        senderLabel.textContent = sender;

        let messageText = document.createElement("span");
        messageText.textContent = data.message;

        li.append(senderLabel, messageText);
        messages.appendChild(li)

        chatblock = document.getElementById("chatMessagesBlock");
        chatblock.scrollTop = chatblock.scrollHeight;
    }
});


socket.on("connect_error", function (error) {
    console.error("Socket Error: ", error);
})

socket.on("disconnect", function () {
    console.error("disconnected");
})