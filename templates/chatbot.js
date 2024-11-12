document.addEventListener("DOMContentLoaded", function () {
    // Elements
    const inputField = document.getElementById('input');
    const messagesContainer = document.getElementById('messages');
    const sendButton = document.getElementById('sendMessage');

    // Send message when user presses 'Enter' or clicks 'Send'
    inputField.addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && inputField.value.trim() !== '') {
            sendMessage();
        }
    });

    sendButton.addEventListener('click', sendMessage);

    // Send the user input to the server and get the chatbot's response
    function sendMessage() {
        const userInput = inputField.value.trim();

        if (userInput !== '') {
            // Display user message
            displayMessage(userInput, 'user');
            inputField.value = '';  // Clear the input field

            // Send the user input to the backend using fetch API
            fetch('/get_response', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_input: userInput })
            })
            .then(response => response.json())
            .then(data => {
                // Display the chatbot's response
                displayMessage(data.response, 'chatbot');
            })
            .catch(error => {
                console.error('Error:', error);
                displayMessage('Sorry, I couldn\'t understand that. Please try again later.', 'chatbot');
            });
        }
    }

    // Display messages in the chat container
    function displayMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add(sender);
        messageDiv.textContent = message;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;  // Scroll to the bottom
    }

    // Initialize the chatbot section with a welcome message
    displayMessage('Hello! How can I assist you today?', 'chatbot');
});
