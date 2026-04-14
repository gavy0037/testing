// 1. IDENTITY & SECURITY GATE
const myUid = sessionStorage.getItem("user_uid");
const myName = sessionStorage.getItem("user_name");

if (!myUid) {
    // If someone tries to access lobby.html without logging in
    // alert("Unauthorized. Please log in via Face Recognition first.");
    // window.location.href = "login.html";
} else {
    // Connect to the WebSocket
    const socket = new WebSocket("ws://localhost:8000/ws/lobby");
    function sendChallenge(targetUid) {
        // Consistent with Python's elif data["type"] == "challenge_request":
        console.log("challenge is begin sent to" , targetUid)
        const message = {
            type: "challenge_request",
            to_player: targetUid,
            from_player: myUid 
        };
        
        socket.send(JSON.stringify(message));
        UI.alert("Challenge sent! Waiting for response...");
    }
    socket.onopen = function(e) {
        console.log("Successfully connected to the Lobby!");
        
        // 2. THE JOIN SIGNAL
        // Consistent with Python's if data["type"] == "join":
        socket.send(JSON.stringify({
            type: "join",
            uid: myUid,
            name: myName
        }));
    };

    socket.onmessage = async function(event) {
        const data = JSON.parse(event.data);
        const playerListDiv = document.getElementById('player-list');

        // 3. HANDLE PLAYER LIST UPDATES
        // Consistent with Python's manager.broadcast({"type": "player_list", ...})
        if (data.type === "player_list") {
            playerListDiv.innerHTML = ''; // Clear the "Waiting..." message

            // We iterate through data.players because the server sends a dictionary
            data.players.forEach(player => {
                // Consistency: Don't show a "Challenge" button for yourself
                if (player.uid !== myUid) {
                    const playerItem = document.createElement('div');
                    playerItem.innerHTML = `
                        <span><strong>${player.name}</strong> (${player.uid})</span>
                        <button onclick="sendChallenge('${player.uid}')">Challenge</button>
                    `;
                    playerListDiv.appendChild(playerItem);
                }
            });
        }

        // 4. HANDLE INCOMING CHALLENGES
        // Consistent with Python's "incoming_challenge" message
        if (data.type === "incoming_challenge") {
            const accept = await UI.confirm(`Player ${data.from_name} (${data.from_uid}) has challenged you! Do you accept?`);
            console.log("Challenge recieved from " , data.from_name)
            // Send response back to Python's elif data["type"] == "challenge_response":
            socket.send(JSON.stringify({
                type: "challenge_response",
                accepted: accept,
                to_player: data.from_uid, // Send back to the challenger
                from_player: myUid        // From me
            }));
        }

        // 5. HANDLE GAME START (Matchmaking Complete)
        if (data.type === "game_start") {
            // Instantly transition both players to the game page without requiring an extra click
            sessionStorage.setItem("current_game_id", data.game_id);
            window.location.href = "game.html"; // Teleport to the 3x3 board
        }

        // 6. HANDLE REJECTION
        if (data.type === "challenge_rejected") {
            UI.alert(data.message);
        }

        // 7. HANDLE LEADERBOARD UPDATES
        if (data.type === "leaderboard") {
            const tbody = document.getElementById("leaderboard-body");
            tbody.innerHTML = "";
            data.players.forEach((player, index) => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${index + 1}</td>
                    <td>${player.name} <span style="opacity:0.5">(${player.uid})</span></td>
                    <td>${player.elo_rating}</td>
                `;
                tbody.appendChild(row);
            });
        }
    };

    
}