import arcade
import random
import numpy as np

# Dimensions de la fenêtre
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
CELL_SIZE = 40
ROWS = SCREEN_HEIGHT // CELL_SIZE
COLS = SCREEN_WIDTH // CELL_SIZE

# Types de cellules
EMPTY = 0
DESTRUCTIBLE = 1
INDESTRUCTIBLE = 2
ACTIONS = ["UP", "DOWN", "LEFT", "RIGHT", "PLACE_BOMB"]


class QLearningAgent:
    def __init__(self, state_size, action_size, alpha=0.1, gamma=0.9, epsilon=0.1, agent_id=0):
        self.state_size = state_size
        self.action_size = action_size
        self.q_table = np.zeros((state_size, action_size))  # Q-Table
        self.alpha = alpha  # Taux d'apprentissage
        self.gamma = gamma  # Facteur de réduction
        self.epsilon = epsilon  # Taux d'exploration
        self.agent_id = agent_id  # Identifiant de l'agent

    def choose_action(self, state):
        """Choisit une action basée sur la politique epsilon-greedy."""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)  # Action aléatoire
        return np.argmax(self.q_table[state])  # Action optimale

    def update(self, state, action, reward, next_state):
        """Met à jour la Q-Table avec la règle Q-Learning."""
        best_next_action = np.max(self.q_table[next_state])
        self.q_table[state, action] += self.alpha * (
            reward + self.gamma * best_next_action - self.q_table[state, action]
        )

    def save_q_table(self, filename):
        """Sauvegarde la Q-Table dans un fichier."""
        np.save(filename, self.q_table)

    def load_q_table(self, filename):
        """Charge la Q-Table depuis un fichier."""
        try:
            self.q_table = np.load(filename)
            print(f"Q-Table chargée depuis {filename}")
        except FileNotFoundError:
            print(f"Fichier {filename} introuvable. Utilisation d'une nouvelle Q-Table.")


class BombermanGame(arcade.Window):
    def __init__(self, num_agents=2, max_episodes=1000):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Bomberman - Multi-Agent Training")
        arcade.set_background_color(arcade.color.BLACK)

        self.num_agents = num_agents
        self.grid = []
        self.agent_positions = []
        self.bombs = []
        self.scores = [0] * num_agents
        self.lives = [3] * num_agents
        self.game_over = [False] * num_agents
        self.current_episode = 0
        self.max_episodes = max_episodes
        self.time_accumulator = 0  # Pour ralentir la vitesse du jeu
        self.update_interval = 0.5  # Temps entre chaque mise à jour (en secondes)

        # Initialiser les agents Q-Learning
        self.agents = [
            QLearningAgent(state_size=ROWS * COLS, action_size=len(ACTIONS), agent_id=i)
            for i in range(num_agents)
        ]

        # Charger les Q-Tables si disponibles
        for i, agent in enumerate(self.agents):
            agent.load_q_table(f"agent_{i+1}_qtable.npy")

    def setup(self):
        """Initialisation du jeu."""
        self.grid = []
        for row in range(ROWS):
            row_data = []
            for col in range(COLS):
                if random.random() < 0.2:
                    row_data.append(DESTRUCTIBLE if random.random() < 0.7 else INDESTRUCTIBLE)
                else:
                    row_data.append(EMPTY)
            self.grid.append(row_data)

        self.agent_positions = [(1, 1 + i * 3) for i in range(self.num_agents)]
        self.scores = [0] * self.num_agents
        self.lives = [3] * self.num_agents
        self.bombs = []
        self.game_over = [False] * self.num_agents

    def get_state(self, agent_index):
        """Convertit la position actuelle d'un agent en un état unique."""
        row, col = self.agent_positions[agent_index]
        return row * COLS + col

    def perform_action(self, agent_index, action):
        """Effectue une action pour un agent."""
        if self.game_over[agent_index]:
            return -100  # Pénalité pour agent mort

        row, col = self.agent_positions[agent_index]

        if action == 0 and row > 0 and self.grid[row - 1][col] == EMPTY:  # UP
            self.agent_positions[agent_index] = (row - 1, col)
            return 5  # Récompense pour mouvement valide
        elif action == 1 and row < ROWS - 1 and self.grid[row + 1][col] == EMPTY:  # DOWN
            self.agent_positions[agent_index] = (row + 1, col)
            return 5
        elif action == 2 and col > 0 and self.grid[row][col - 1] == EMPTY:  # LEFT
            self.agent_positions[agent_index] = (row, col - 1)
            return 5
        elif action == 3 and col < COLS - 1 and self.grid[row][col + 1] == EMPTY:  # RIGHT
            self.agent_positions[agent_index] = (row, col + 1)
            return 5
        elif action == 4:  # PLACE_BOMB
            self.bombs.append({"row": row, "col": col, "timer": 3, "owner": agent_index})
            return 0  # Pas de récompense immédiate pour poser une bombe
        return -1  # Récompense négative pour une action invalide

    def explode_bomb(self, bomb):
        """Gère l'explosion d'une bombe."""
        row, col = bomb["row"], bomb["col"]
        affected_positions = [(row, col)]

        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            for i in range(1, 3):
                r, c = row + dr * i, col + dc * i
                if 0 <= r < ROWS and 0 <= c < COLS:
                    if self.grid[r][c] == INDESTRUCTIBLE:
                        break
                    affected_positions.append((r, c))
                    if self.grid[r][c] == DESTRUCTIBLE:
                        self.grid[r][c] = EMPTY
                        break

        for i, (arow, acol) in enumerate(self.agent_positions):
            if (arow, acol) in affected_positions and not self.game_over[i]:
                self.lives[i] -= 1
                if self.lives[i] <= 0:
                    self.game_over[i] = True

    def on_draw(self):
        """Affiche la grille et les statistiques."""
        self.clear()
        for row in range(ROWS):
            for col in range(COLS):
                x = col * CELL_SIZE + CELL_SIZE // 2
                y = row * CELL_SIZE + CELL_SIZE // 2
                if self.grid[row][col] == DESTRUCTIBLE:
                    arcade.draw_rectangle_filled(x, y, CELL_SIZE, CELL_SIZE, arcade.color.RED)
                elif self.grid[row][col] == INDESTRUCTIBLE:
                    arcade.draw_rectangle_filled(x, y, CELL_SIZE, CELL_SIZE, arcade.color.GRAY)
                else:
                    arcade.draw_rectangle_filled(x, y, CELL_SIZE, CELL_SIZE, arcade.color.BLACK)
                    arcade.draw_rectangle_outline(x, y, CELL_SIZE, CELL_SIZE, arcade.color.WHITE)

        for i, (row, col) in enumerate(self.agent_positions):
            if not self.game_over[i]:
                x = col * CELL_SIZE + CELL_SIZE // 2
                y = row * CELL_SIZE + CELL_SIZE // 2
                color = arcade.color.BLUE if i == 0 else arcade.color.GREEN
                arcade.draw_circle_filled(x, y, CELL_SIZE // 3, color)

        for bomb in self.bombs:
            x = bomb["col"] * CELL_SIZE + CELL_SIZE // 2
            y = bomb["row"] * CELL_SIZE + CELL_SIZE // 2
            arcade.draw_circle_filled(x, y, CELL_SIZE // 4, arcade.color.YELLOW)

        for i, (score, lives) in enumerate(zip(self.scores, self.lives)):
            arcade.draw_text(f"Agent {i+1} - Score: {score}, Lives: {lives}",
                             10, SCREEN_HEIGHT - 20 * (i + 1), arcade.color.WHITE, font_size=12)

    def on_update(self, delta_time):
        """Met à jour l'état du jeu."""
        self.time_accumulator += delta_time
        if self.time_accumulator < self.update_interval:
            return
        self.time_accumulator = 0

        for bomb in self.bombs[:]:
            bomb["timer"] -= self.update_interval
            if bomb["timer"] <= 0:
                self.explode_bomb(bomb)
                self.bombs.remove(bomb)

        for i in range(self.num_agents):
            if self.game_over[i]:
                continue
            current_state = self.get_state(i)
            action = self.agents[i].choose_action(current_state)
            reward = self.perform_action(i, action)
            next_state = self.get_state(i)
            self.agents[i].update(current_state, action, reward, next_state)

        if all(self.game_over):
            print(f"Épisode {self.current_episode + 1} terminé. Réinitialisation du jeu.")
            self.current_episode += 1
            for i, agent in enumerate(self.agents):
                agent.save_q_table(f"agent_{i+1}_qtable.npy")
            self.setup()


if __name__ == "__main__":
    game = BombermanGame(num_agents=3)
    game.setup()
    arcade.run()
