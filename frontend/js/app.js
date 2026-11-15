
const serverStatus = document.getElementById("server-status");
const dataMode = document.getElementById("data-mode");

const chatForm = document.getElementById("chat-form");
const sendButton = document.getElementById("send-button");
const questionInput = document.getElementById("user-question");
const chatMessages = document.getElementById("chat-messages");

const refreshButton = document.getElementById("refresh-button");

let chatHistory = [];


function updateClock() {

    const clock = document.getElementById("live-clock");

    clock.textContent = new Date().toLocaleString();

}

updateClock();

setInterval(updateClock, 1000);


// Create safe chat messages using textContent
function addMessage(role, text) {

    const message = document.createElement("div");

    message.className =
        role === "user" ? "user-message" : "bot-message";

    if (role === "model") {

        const title = document.createElement("strong");

        title.textContent = "MediAssist AI";

        message.appendChild(title);

    }

    const content = document.createElement("div");

    content.className = "ai-answer";

    content.textContent = text;

    message.appendChild(content);

    chatMessages.appendChild(message);

    chatMessages.scrollTop = chatMessages.scrollHeight;

    return message;

}


// Dashboard loading
async function loadDashboard() {

    dataMode.textContent = "Loading sample readings...";

    try {

        const response = await fetch("/api/status");

        if (!response.ok) {
            throw new Error("Backend unavailable");
        }

        const status = await response.json();

        serverStatus.textContent = "● Backend Online";
        serverStatus.classList.add("online");

        if (!status.gemini_connected) {
            serverStatus.textContent = "● Gemini Not Configured";
        }

        const vitalsResponse = await fetch("/api/vitals");

        if (!vitalsResponse.ok) {
            throw new Error("Unable to load readings");
        }

        const data = await vitalsResponse.json();

        document.getElementById("heart-rate").textContent =
            data.heart_rate;

        document.getElementById("temperature").textContent =
            data.temperature;

        document.getElementById("spo2").textContent =
            data.spo2;

        dataMode.textContent =
            "Data mode: " + data.mode +
            ". These are sample values, not real measurements.";

        document.getElementById("last-updated").textContent =
            "Last updated: " + new Date().toLocaleTimeString();

    }

    catch (error) {

        serverStatus.textContent = "● Backend Offline";
        serverStatus.classList.remove("online");

        dataMode.textContent =
            "Unable to load readings. Please check the backend.";

        console.error("Dashboard error:", error);

    }

}


refreshButton.addEventListener("click", loadDashboard);


// Send question to Gemini through Flask
chatForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    if (sendButton.disabled) {
        return;
    }

    addMessage("user", question);

    questionInput.value = "";

    sendButton.disabled = true;
    sendButton.textContent = "Thinking...";

    const loadingMessage = addMessage(
        "model",
        "MediAssist AI is preparing your answer..."
    );

    try {

        const response = await fetch("/api/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                question: question,

                history: chatHistory.slice(-12)

            })

        });


        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.error || "Unable to generate an answer."
            );

        }


        const answer = data.answer;

        loadingMessage.querySelector(".ai-answer").textContent =
            answer;


        // Maintain recent conversation context
        chatHistory.push(
            { role: "user", text: question },
            { role: "model", text: answer }
        );

        chatHistory = chatHistory.slice(-12);

        chatMessages.scrollTop = chatMessages.scrollHeight;

    }

    catch (error) {

        loadingMessage.querySelector(".ai-answer").textContent =
            "Sorry, an error occurred: " + error.message;

        console.error("AI chat error:", error);

    }

    finally {

        sendButton.disabled = false;
        sendButton.textContent = "Send ➤";

        questionInput.focus();

    }

});


// Start dashboard
loadDashboard();
