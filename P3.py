import socket
import threading
import time
import logging
import json
from HeartbeatManager import HeartbeatManager
from ConsensusManager import ConsensusManager

class GameLogic:
    def __init__(self):
        self.QUIT_COMMAND = "quit"
        self.QUIT_TEXT = "Quitting the game."
        self.grid_size = 6
        self.board = [[" "] * self.grid_size for _ in range(self.grid_size)]
        self.turn = "X"
        self.you = "O"
        self.player2 = "X"
        self.player3 = "Y"
        self.winner = None
        self.game_over = False
        self.other_players = []
        self.hb_players = {}
        self.counter = 0 
        self.host_port = 9999
        self.hb1_port=53224
        self.host = "localhost"
        self.player2_port=9998
        self.player2_address="localhost"
        self.p1_port=53218
        self.p2_port=53219
        environment = input("Running locally?")
        env_lower = environment.lower()
        if env_lower != "yes":
            player_number = input("What is your player number?")
            self.load_config("config.json", player_number)
            
        
        #sm modified it
        # Create a ConsensusManager instance with all players
        self.consensus_manager = ConsensusManager()
        self.configure_logging()

    def configure_logging(self):
            # Configure logging for the main log file
            self.main_logger = logging.getLogger('main')
            self.main_logger.setLevel(logging.DEBUG)

            # Add a FileHandler for the main log file
            self.main_logger.addHandler(logging.FileHandler(f'TicTacLog{self.you}.log'))

            # Create a formatter and add it to the handler
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            self.main_logger.handlers[0].setFormatter(formatter)

            # Configure logging for the heartbeat log file
            self.heartbeat_logger = logging.getLogger('heartbeat')
            self.heartbeat_logger.setLevel(logging.DEBUG)

            # Add a FileHandler for the heartbeat log file
            self.heartbeat_logger.addHandler(logging.FileHandler(f'HeartbeatLog{self.you}.log'))

            # Create a formatter and add it to the handler
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            self.heartbeat_logger.handlers[0].setFormatter(formatter)
        
    
    def load_config(self, config_file, player_number):
        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)

            self.host = config_data["1"]["host"]
            self.host_port = config_data["1"]["port"]
            self.p1_port = config_data["1"]["hb_port"]
            self.player2_address = config_data["2"]["host"]
            self.player2_port = config_data["2"]["port"]
            self.p2_port = config_data["2"]["hb_port"]

        except FileNotFoundError:
            print(f"Config file {config_file} not found.")
            self.main_logger.info(f"Config file {config_file} not found.")
            exit()
        except json.JSONDecodeError:
            print(f"Error decoding JSON in {config_file}.")
            self.main_logger.info(f"Error decoding JSON in {config_file}.")
            exit()
        except KeyError:
            print(f"Invalid configuration for node {self.you}.")
            self.main_logger.info(f"Invalid configuration for node {self.you}.")
            exit()

    # Connect to sockets opened by P1 and P2
    def connect_to_game(self): 
            try:
                self.main_logger.info(f'{self.you} started the game')
                host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                host_socket.connect((self.host, self.host_port))
                self.other_players.append(host_socket)
                print("Connected to P1")

                player_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                player_socket.connect((self.player2_address, self.player2_port))
                self.other_players.append(player_socket)
                player_socket.send("Hello P2".encode())
                data = player_socket.recv(1024)
                message = data.decode()
                if message == "Hello P3":
                    print("P2 and P3 are connected.")
                else:
                    print("Failed to connect to P2.")
                # sm modified it from here
                consensus_manager = ConsensusManager()
                consensus_manager.start_consensus()

                p1_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                p1_socket.connect((self.host, self.p1_port))
                p2_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                p2_socket.connect((self.host, self.p2_port))
                
                self.hb_players["P1"]= p1_socket
                self.hb_players["P2"]=p2_socket
                
                try:
                    print("Trying to connect to P2.")
                    threading.Thread(target=self.handle_connection, args=(player_socket,"P2",[player_socket,host_socket])).start()
                except:
                    print("Failed to connect to P2.")
                threading.Thread(target=self.handle_connection, args=(host_socket,"P1",[host_socket,player_socket])).start()
            
            except (socket.error, BrokenPipeError, ConnectionResetError) as e:
                print(f"Socket disconnected. The game will quit. {e} ")
                # exit()
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                self.inform_disconnect(None, self.other_players)
                
        # sm modified it
    def get_game_state(self):
        # Return the current game state (in this case, the board)
        return self.board



    def handle_connection(self, client_socket,player,other_players):
        while player=="P1":
            data = client_socket.recv(1024)
            if data.decode() == "All players connected.":
                print("All players connected.")
                client_socket.send("ACK".encode()) 
                break
        self.heartbeat_manager = HeartbeatManager("P3", self.hb_players,self.heartbeat_logger)
        threading.Thread(target=self.heartbeat_manager.hb_start, daemon=True).start()
        while not self.game_over:
            #print(player)
            #print("after all players con")
            data = client_socket.recv(1024)
            message = data.decode()
            #print(f"Received message: {message} from {player}")

            if "disconnect" in message.lower():
                print(message)
                self.game_over = True
                exit()
            elif message.startswith("WIN"):
                print("YOU LOSE!")
                self.game_over = True
                self.close_game()
                exit()
            elif message.startswith("TIE"):
                print("IT IS A TIE!")
                self.game_over = True
                self.close_game()
                exit()
            elif message.startswith("move:"):
                move, player_symbol = data.decode().split(":")[1].split(",")[:2], data.decode().split(":")[1].split(",")[2]
                if player_symbol != self.you:
                    self.apply_move(move, player_symbol,other_players)
            elif message.startswith("next_turn:"):
                self.turn=message.split(":")[1]
                # If the message from the host indicates it's this player's turn, make a move
                if message.split(":")[1] == self.you:
                    # sm modified it
                    self.reach_consensus_before_move(other_players)
                    # to here
                    while True:
                        move = input("Enter your move: ")
                        if move.lower() == self.QUIT_COMMAND:
                            print(self.QUIT_TEXT)
                            for other_player in other_players:
                                other_player.send(self.QUIT_TEXT.encode())
                            self.game_over = True
                            break
                        elif self.check_valid_move(move.split(",")):
                            self.apply_move(move.split(","), self.you,other_players)
                            self.main_logger.info(f"Movement {self.you} {move}")
                            self.main_logger.info(f"Board {self.board}")
                            # Include the player's symbol in the move message
                            for other_player in other_players:
                                other_player.send(("move:" + move + "," + self.you).encode("utf-8"))
                            break
                        else:
                            print("Invalid move. Try Again.")
            else:
                # print("messa",message)
                # print("No data received from server.")
                time.sleep(1)

        # sm modified it
    def reach_consensus_before_move(self, other_players):
        print("Requesting consensus before making a move...")
        if not self.consensus_manager.start_consensus():
            self.inform_disconnect(None, other_players)
            return
        print("Consensus reached. Proceeding with the move.")       
                
                 
    def next_turn(self):
        if self.turn == self.you:
            return self.player2
        elif self.turn == self.player2:
            return self.player3
        else:
            return self.you

    def apply_move(self, move, player,other_players): 
        try:

            if self.game_over:
                return
            self.counter += 1
            self.board[int(move[0])][int(move[1])] = player
            self.print_board()
            
            if self.check_for_winner():
                self.game_over = True
                if self.winner == self.you:
                    print("YOU WIN!!")  
                    #broadcast a win, have other players print they lost then quit
                    for other_player in other_players:
                            other_player.send(("WIN" + self.you).encode("utf-8"))
                            
                    self.game_over = True

                else:
                    if self.counter == 36:
                        print("IT IS A TIE!")
                        for other_player in other_players:
                            other_player.send("TIE" + self.you.encode("utf-8"))
                        self.game_over = True
                        #broadcast a tie then quit
                exit()
        except IndexError:
            self.main_logger.error("Invalid row or column index. Please choose valid row and column indexes.")
        except ValueError as e:
            self.main_logger.error(f"Error: {e}")

    def check_valid_move(self, move):
        try:
            row, col = int(move[0]), int(move[1])
            # Check if the given indices are within the valid range (0 to 5 for a 6x6 board)
            if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                return move != self.QUIT_COMMAND and self.board[row][col] == " "
            else:
                self.main_logger.error("Invalid row or column index. Please choose valid row and column indexes.")
                return False
        except ValueError:
            self.main_logger.error("Invalid row or column index. Please enter integer values.")
        return False

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
                return True
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
        # DIAGONAL CHECKS
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
    
    def inform_disconnect(self,disconnected_player, other_players):
        message = "An error occurred. Game will quit" 
        if  disconnected_player:
            message = f"Player {disconnected_player} has disconnected. Game will quit"
    
        for player in other_players:
            player.send(message.encode("utf-8"))
            player.close()
        self.main_logger.info("Disconnect informed, quitting.")
        exit()

    def close_game(self):
        self.heartbeat_manager.set_geme_over(self.game_over)
        # Close all player sockets
       # for player_socket in self.other_players:
        #    player_socket.close()

        # Close heartbeat sockets
       # for hb_socket in self.hb_players.values():
          #  hb_socket.close()

        print("Game is closed.")

    def print_board(self):
        print("\n")
        for row in range(6):
            print(" | ".join(self.board[row]))
            if row != 5:
                print("-----------------------------")
        print("\n")
        
def main():
    game = GameLogic()
    game.connect_to_game()

if __name__ == "__main__":
    main()
