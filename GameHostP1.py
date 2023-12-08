import socket
import threading

class GameLogic:
    def __init__(self):
        self.board = [[" "] * 6 for _ in range(6)]
        self.turn = "X"
        self.you = "X"
        self.player2 = "Y"
        self.player3 = "O"
        self.winner = None
        self.game_over = False

        self.counter = 0  # to dtermien a tie if all field are full, counter is 36, we have a tie if no winner etc

    def host_game(self, host, port):  # basically does job fo tournament manager?
        host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # we are using tcp
        host_socket.bind((host, port))
        host_socket.listen(2)  # server needs to listen for 2 connections so that the game can start
        
        print("Waiting for players to connect...")
        player2_socket, player2_address = host_socket.accept()
        print("Player 2 connected!",player2_address)
        player3_socket, player3_address = host_socket.accept()
        print("Player 3 connected!", player3_address)

        player2_socket.send("All players connected.".encode())
        player3_socket.send("All players connected.".encode())

        threading.Thread(target=self.handle_connection, args=(player2_socket, [player2_socket,player3_socket],self.player2,1)).start()
        threading.Thread(target=self.handle_connection, args=(player3_socket, [player3_socket,player2_socket],self.player3,0)).start()
        # shoudl i close it? hit technically u will get the other moves and evrtg mn otehr nodes

    def handle_connection(self,player,other_players,symbol,flag):
            while not self.game_over:
                if self.turn == self.you and flag==1:  # do we do this for turns
                    move = input("Enter a move (row,column): ")
                    if self.check_valid_move(move.split(",")):
                        self.apply_move(
                            move.split(","), self.you
                        )  # hadi wstah should have smtg fo share game state w keep track of games state
                        #is this ok to handle turns
                            # idk maybe look into mroe of how ur gonna ensure consistency w synchro han
                    # invalid move
                        self.turn = self.next_turn()
                        for other_player in other_players:
                            other_player.send(("move:" + move + "," + self.you).encode("utf-8"))
                            other_player.send(("next_turn:" + self.turn).encode("utf-8"))
                        print("Valid move, to the next!")
                    else:
                        print("Invalid move!")  # what to do in this case? i guess you can enter a new mve hit rak wst loop
                elif self.turn==symbol:
                    # take in the data received from other players, check why bdbt this nbr
                    data = player.recv(1024)

                    if not data:
                        # why close clients HNA I GUESS FAULT TOLERANCE
                        # IF SMTG GOES DOWN WHAT TP DO? do we just lose teh con
                        print("no data from ", player)
                        break
                    move, player_symbol = data.decode().split(":")[1].split(",")[:2], data.decode().split(":")[1].split(",")[2]
                    self.apply_move(move, player_symbol)
                    self.turn = self.next_turn()
                    for other_player in other_players:
                        other_player.send(("move:"+ "," .join(move) + "," + player_symbol).encode("utf-8"))
                        other_player.send(("next_turn:" + self.turn).encode("utf-8"))
                        print("ha next turn lmn",self.turn)


    def next_turn(self):
        if self.turn == self.you:
            return self.player2
        elif self.turn == self.player2:
            return self.player3
        else:
            return self.you
    # WHAT TO DO IF UR THRONW OUT OF THE LOOP CLOSE TEH CLIENTS?
    def apply_move(self, move, player):  # idk arguments i guess aybano as we go,
        # i think correct hit player hia bach tayl3bp
        if self.game_over:  # HIT GAME OVER?? MAKHASSOCH YWSL HNA LA KAN GAME OVER NO?
            return
        self.counter += 1
        self.board[int(move[0])][int(move[1])] = player
        self.print_board()
        if self.check_for_winner():
            self.game_over = True
            if self.winner == self.you:
                print("YOU WIN!!")  # what happens when someone wins???
            elif self.winner == self.player2 or self.winner == self.player3:
                print("YOU LOOSE! :(")
            else:
                if self.counter == 36:
                    print("IT IS A TIE!")
            exit()  # should you exit if winner found or hwats the next step thatw e have to do

    def check_valid_move(self, move):
        return self.board[int(move[0])][int(move[1])] == " "

    def check_for_winner(self):
        for row in range(6):
            count = 0
            for col in range(5):
                if (
                    self.board[row][col] == self.board[row][col + 1]
                    and self.board[row][col] != " "
                ):
                    count += 1
            if count == 5:
                self.winner = self.board[row][0]
                self.game_over = True
                return True  # NYTHING ELSE TO DO IF TEHRE IS A WINNER???
        for col in range(6):
            count = 0
            for row in range(5):
                if (
                    self.board[row][col] == self.board[row+1][col]
                    and self.board[row][col] != " "
                ):
                    count += 1
            if count == 5:
                self.winner = self.board[0][col]
                self.game_over = True
                return True
        # DIIAG CHECKS
        count_diag1 = 0
        count_diag2 = 0
        for i in range(5):
            if self.board[i][i] == self.board[i + 1][i + 1] and self.board[i][i] != " ":
                count_diag1 += 1
            if (
                self.board[i][5 - i] == self.board[i + 1][4 - i]
                and self.board[i][5 - i] != " "
            ):
                count_diag2 += 1

        if count_diag1 == 5 and self.board[0][0] != " ":
            self.winner = self.board[0][0]
            self.game_over = True
            return True
        elif count_diag2 == 5 and self.board[0][5] != " ":
            self.winner = self.board[0][5]
            self.game_over = True
            return True
        return False

    def print_board(self):
        print("\n")
        for row in range(6):
            print(" | ".join(self.board[row]))
            if row != 5:
                print("--------------------------------")
        print("\n")

game = GameLogic()
port = 9999
host = "localhost"
game.host_game(host, port)