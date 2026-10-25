console.log("Here12")

var socket = io();

document.getElementById("message").addEventListener("keyup", function (event) {
    if (event.key == "Enter") {
        let message = document.getElementById("message").value;
        console.log(message)
        socket.emit("new_message", message);
        document.getElementById("message").value = "";
    }
});

socket.on("chat", function (data) {
    let ul = document.getElementById("chat-messages");
    let li = document.createElement("li");
    li.appendChild(document.createTextNode(data["username"] + ": "+ data["message"]));
    ul.appendChild(li);
    ul.scrolltop = ul.scrollHeight;

});