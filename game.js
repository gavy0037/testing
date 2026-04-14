// i need to do something for room id.
        const roomId = sessionStorage.getItem("current_game_id") || "test_room";
        const ws = new WebSocket(`ws://localhost:8000/ws/room/${roomId}`)

        ws.onopen = () =>{
            console.log("Connected to room");
        }


        function makeMove(cellIndex){
            const moveData = {
                type: "move",
                index: cellIndex
            }

            ws.send(JSON.stringify(moveData))
        }
        ws.onmessage = (event)=>{
            const data =  JSON.parse(event.data)

            console.log("Recived : " , data)

            switch(data.type){
                case "init":
                    console.log("My assigned symbol:",data.symbol)
                    UI.alert(data.message)
                    break;
                case "start":
                    console.log("Game started , Turn : " ,data.your_turn)
                    break;
                case "move":
                    let cell = document.querySelector(`[data-index="${data.index}"]`);
                    cell.innerText = data.symbol;
                    // Provide aesthetic coloring based on symbol
                    cell.style.color = data.symbol === "X" ? "var(--x-color)" : "var(--o-color)";
                    cell.setAttribute('data-index' , '-1')
                    cell.style.pointerEvents = "none";
                    break ;
                case "result":
                    setTimeout(() => {
                        UI.toast(data.status == "win" ? `Player ${data.winner} won!\n\nReturning to lobby in 3 seconds...` : "It's a draw!\n\nReturning to lobby in 3 seconds...").then(() => {
                            window.location.href = "lobby.html";
                        });
                    }, 100);
                    break ;
                case "error":
                    UI.alert("oops : " + data.message);
                    break ;
                case "system":
                    UI.toast(data.message).then(() => {
                        window.location.href = "lobby.html";
                    });
                    break;
            }
        }

        document.querySelectorAll(".cell").forEach(cell =>{
            cell.addEventListener('click',()=>{
                const index = Number(cell.getAttribute('data-index'));
                console.log("attemt of move at index :" , index)
                if(index != -1) makeMove(Number(index)); // this has been added so that if user presses a already occupied cell , then nothing will happen , if they change js in inspect and then try to cheat ,then a aleart from backend will come
            })
        })