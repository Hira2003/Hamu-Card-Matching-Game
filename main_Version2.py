import sys
import os
import json
import random
from glob import glob
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QMessageBox, QStackedWidget, QGridLayout, QSizePolicy, QDialog
)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer, QEvent

import pygame  # For sound

SAVE_FILE = "progress.json"
LEVELS_DIR = "levels"
TOTAL_LEVELS = 10

SOUNDS_DIR = "sounds"
IMAGES_DIR = "images"
MAIN_IMAGE = os.path.join(IMAGES_DIR, "main_pic.png")       # Main menu pic
CONGRATS_IMAGE = os.path.join(IMAGES_DIR, "win.png")     # Last level congrats pic
BG_MUSIC = os.path.join(SOUNDS_DIR, "bg_music.mp3")           # Background music for game
CLAP_SOUND = os.path.join(SOUNDS_DIR, "clap.wav")             # Clapping sound for last level

# --- Theme Helper ---
class Theme:
    MAIN_BG = "#1a1a2e"
    ACCENT = "#a259ff"
    WHITE = "#ffffff"
    BTN_BG = "#2d2d44"
    BTN_TEXT = "#f3e6ff"
    DISABLED_BTN_BG = "#3a3a4d"
    CARD_BG = "#d1b3ff"
    
    @staticmethod
    def apply(app):
        app.setStyleSheet(f"""
            QWidget {{
                background: {Theme.MAIN_BG};
                color: {Theme.WHITE};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 15px;
            }}
            QLabel#titleLabel {{
                font-size: 28px;
                font-weight: bold;
                color: {Theme.ACCENT};
                margin-bottom: 16px;
            }}
            QPushButton {{
                background: {Theme.BTN_BG};
                border-radius: 12px;
                color: {Theme.BTN_TEXT};
                padding: 0;
                font-size: 22px;
                min-width: 120px;
            }}
            QPushButton:pressed {{
                background: {Theme.ACCENT};
                color: {Theme.WHITE};
            }}
            QPushButton:disabled {{
                background: {Theme.DISABLED_BTN_BG};
                color: #777;
            }}
            #contactBtn {{
                background: transparent;
                color: {Theme.ACCENT};
                border: none;
                font-size: 19px;
                font-weight: bold;
                text-decoration: underline;
                margin-bottom: 8px;
            }}
        """)

def get_grid_size_for_level(level):
    if level in [1, 2]:
        return (4, 4)
    elif level in [3, 4]:
        return (5, 4)
    elif level in [5, 6]:
        return (5, 6)
    elif level in [7, 8]:
        return (6, 6)
    elif level in [9, 10]:
        return (6, 7)
    else:
        return (4, 4)

def load_progress():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {"unlocked_level": 1}

def save_progress(progress):
    with open(SAVE_FILE, "w") as f:
        json.dump(progress, f)

class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self.button_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "button_click.wav"))
        self.card_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "card_flip.wav"))
        self.match_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "match.wav"))
        self.win_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "win.wav"))
        self.clap_sound = pygame.mixer.Sound(CLAP_SOUND) if os.path.exists(CLAP_SOUND) else None
        self.bg_music_loaded = False
        self.bg_music_path = BG_MUSIC
        self.bg_music_volume = 0.15

    def play_button(self):
        self.button_sound.play()
    
    def play_card(self):
        self.card_sound.play()

    def play_match(self):
        self.match_sound.play()

    def play_win(self):
        self.win_sound.play()

    def play_clap(self):
        if self.clap_sound:
            self.clap_sound.play()

    def play_bg_music(self):
        if os.path.exists(self.bg_music_path):
            try:
                pygame.mixer.music.load(self.bg_music_path)
                pygame.mixer.music.set_volume(self.bg_music_volume)
                pygame.mixer.music.play(-1)  # Loop forever
                self.bg_music_loaded = True
            except Exception as e:
                print("Could not play bg music:", e)

    def stop_bg_music(self):
        if self.bg_music_loaded:
            pygame.mixer.music.stop()
            self.bg_music_loaded = False

class CongratsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Congratulations!")
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        layout = QVBoxLayout()
        label = QLabel("🎉<br><b>Congratulations!<br>You have completed all levels!<br>You are a real Memory Master!</b><br>🎉")
        label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {Theme.ACCENT};")
        label.setTextFormat(Qt.RichText)
        layout.addSpacing(10)
        layout.addWidget(label)
        if os.path.exists(CONGRATS_IMAGE):
            img_label = QLabel()
            pix = QPixmap(CONGRATS_IMAGE).scaled(340, 340, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)
        layout.addSpacing(10)
        btn = QPushButton("Back to Main Menu")
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setMinimumHeight(48)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        self.setLayout(layout)
        self.setFixedSize(400, 520 if os.path.exists(CONGRATS_IMAGE) else 320)

class MainMenu(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Matching Pics Game", objectName="titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(16)

        # Main image (optional, now below title)
        if os.path.exists(MAIN_IMAGE):
            img_label = QLabel()
            pix = QPixmap(MAIN_IMAGE)
            pix = pix.scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)
            layout.addSpacing(16)

        # Responsive button settings
        btn_min_height = 48
        btn_max_height = 90
        btn_min_width = 150
        btn_max_width = 500

        def make_button(text, slot):
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(btn_min_height)
            btn.setMaximumHeight(btn_max_height)
            btn.setMinimumWidth(btn_min_width)
            btn.setMaximumWidth(btn_max_width)
            btn.clicked.connect(slot)
            return btn

        layout.addStretch(1)
        btn_new = make_button("New Game", self.on_new_game)
        layout.addWidget(btn_new)
        layout.addSpacing(10)
        btn_continue = make_button("Continue", self.on_continue)
        layout.addWidget(btn_continue)
        layout.addSpacing(10)
        btn_exit = make_button("Exit", self.on_exit)
        layout.addWidget(btn_exit)
        layout.addSpacing(16)
        layout.addStretch(1)

        # Contact Section (clear and visible)
        contact_layout = QHBoxLayout()
        contact_layout.setAlignment(Qt.AlignCenter)
        contact_btn = QPushButton("Contact Developer")
        contact_btn.setObjectName("contactBtn")
        contact_btn.setFixedSize(220, 38)
        contact_btn.clicked.connect(self.contact_me)
        contact_layout.addWidget(contact_btn)
        layout.addLayout(contact_layout)

        contact_info = QLabel("For support or feedback, email: hirafuyu2003@gmail.com")
        contact_info.setAlignment(Qt.AlignCenter)
        contact_info.setStyleSheet("color:#a259ff; font-size:15px; margin-top:0; margin-bottom:8px;")
        layout.addWidget(contact_info)

        self.setLayout(layout)
    def on_new_game(self):
        self.parent.sound_manager.play_button()
        self.parent.show_levels()
    def on_continue(self):
        self.parent.sound_manager.play_button()
        self.parent.show_levels()
    def on_exit(self):
        self.parent.sound_manager.play_button()
        QApplication.quit()
    def contact_me(self):
        self.parent.sound_manager.play_button()
        QMessageBox.information(self, "Contact Developer", "Contact Hira\nEmail: hirafuyu2003@gmail.com")

class LevelsPage(QWidget):
    def __init__(self, parent, unlocked_level):
        super().__init__()
        self.parent = parent
        self.unlocked_level = unlocked_level
        self.init_ui()
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        title = QLabel("Select Level", objectName="titleLabel")
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)
        self.btns_layout = QHBoxLayout()
        self.level_buttons = []
        for i in range(1, TOTAL_LEVELS + 1):
            btn = QPushButton(str(i))
            btn.setFixedSize(48, 48)
            btn.setEnabled(i <= self.unlocked_level)
            btn.clicked.connect(lambda _, x=i: self.level_btn_clicked(x))
            self.btns_layout.addWidget(btn)
            self.level_buttons.append(btn)
        self.layout.addLayout(self.btns_layout)
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.on_back)
        self.layout.addWidget(back_btn)
        self.setLayout(self.layout)
    def update_unlocks(self, unlocked_level):
        self.unlocked_level = unlocked_level
        for i, btn in enumerate(self.level_buttons):
            btn.setEnabled(i + 1 <= self.unlocked_level)
    def level_btn_clicked(self, level):
        self.parent.sound_manager.play_button()
        self.parent.start_level(level)
    def on_back(self):
        self.parent.sound_manager.play_button()
        self.parent.show_main_menu()

class GamePage(QWidget):
    def __init__(self, parent, level):
        super().__init__(parent)
        self.parent = parent
        self.level = level
        self.rows, self.cols = get_grid_size_for_level(self.level)
        self.cards = []
        self.setMinimumSize(400, 400)
        self.init_ui()
        self.installEventFilter(self)

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.title = QLabel(f"Level {self.level}", objectName="titleLabel")
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)

        self.grid_widget = QWidget()
        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        self.grid.setContentsMargins(10, 10, 10, 10)
        self.grid.setAlignment(Qt.AlignCenter)
        self.grid_widget.setLayout(self.grid)
        self.layout.addWidget(self.grid_widget, alignment=Qt.AlignCenter)

        self.status_label = QLabel("Find all pairs!")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        self.back_btn = QPushButton("Back to Levels")
        self.back_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.back_btn.clicked.connect(self.on_back)
        self.layout.addWidget(self.back_btn, alignment=Qt.AlignBottom)

        self.setLayout(self.layout)
        self.prepare_game()

    def get_best_card_size(self):
        main_window = self.parent.window()
        screen = QApplication.primaryScreen().availableGeometry()
        win_width = main_window.width() if main_window.width() > 100 else screen.width()
        win_height = main_window.height() if main_window.height() > 100 else screen.height()
        reserved_height = 60 + 40 + 64 + 40  # title + status + back btn + margin
        reserved_width = 40  # margin
        available_height = win_height - reserved_height
        available_width = win_width - reserved_width
        spacing = self.grid.spacing()
        borders = 4

        card_width = (available_width - (self.cols - 1) * spacing - borders * self.cols) // self.cols
        card_height = (available_height - (self.rows - 1) * spacing - borders * self.rows) // self.rows
        card_size = max(36, min(card_width, card_height, 160))
        return card_size

    def resizeEvent(self, event):
        self.update_card_sizes()
        super().resizeEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show:
            QTimer.singleShot(50, self.update_card_sizes)
        return super().eventFilter(obj, event)

    def update_card_sizes(self):
        size = self.get_best_card_size()
        for btn in self.cards:
            btn.setFixedSize(size, size)
            btn.setIconSize(QSize(size - 8, size - 8))

    def prepare_game(self):
        level_folder = os.path.join(LEVELS_DIR, f"level{self.level}")
        images = glob(os.path.join(level_folder, "*.png")) + glob(os.path.join(level_folder, "*.jpg"))
        pair_count = (self.rows * self.cols) // 2
        if len(images) < pair_count:
            QMessageBox.critical(self, "Error", f"Not enough images in {level_folder}.\nNeed at least {pair_count} images.")
            self.back_to_levels()
            return
        chosen_imgs = random.sample(images, pair_count)
        card_imgs = chosen_imgs * 2
        random.shuffle(card_imgs)
        self.card_imgs = card_imgs
        self.cards = []
        self.cards_state = [False] * len(card_imgs)
        self.flipped_indices = []
        self.completed = set()

        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget: widget.setParent(None)

        size = self.get_best_card_size()
        k = 0
        for row in range(self.rows):
            for col in range(self.cols):
                if k >= len(card_imgs): continue
                btn = QPushButton("")
                btn.setFixedSize(size, size)
                btn.setStyleSheet(f"background:{Theme.CARD_BG}; border:2px solid {Theme.ACCENT};")
                btn.setIconSize(QSize(size - 8, size - 8))
                btn.clicked.connect(lambda _, idx=k: self.card_clicked(idx))
                btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                self.cards.append(btn)
                self.grid.addWidget(btn, row, col)
                k += 1

    def card_clicked(self, idx):
        if idx in self.completed or idx in self.flipped_indices or len(self.flipped_indices) >= 2:
            return
        self.parent.sound_manager.play_card()
        btn = self.cards[idx]
        pix = QPixmap(self.card_imgs[idx])
        btn.setIcon(QIcon(pix))
        btn.setText("")
        self.flipped_indices.append(idx)
        if len(self.flipped_indices) == 2:
            a, b = self.flipped_indices
            if os.path.basename(self.card_imgs[a]) == os.path.basename(self.card_imgs[b]):
                self.completed.add(a)
                self.completed.add(b)
                self.status_label.setText("Matched!")
                self.parent.sound_manager.play_match()
                self.flipped_indices.clear()
                if len(self.completed) == len(self.cards):
                    QTimer.singleShot(300, self.win_level)
            else:
                self.status_label.setText("No match!")
                QApplication.processEvents()
                QTimer.singleShot(700, self.hide_unmatched)

    def hide_unmatched(self):
        a, b = self.flipped_indices
        for idx in [a, b]:
            btn = self.cards[idx]
            btn.setIcon(QIcon())
            btn.setText(" ")
        self.flipped_indices.clear()
        self.status_label.setText("Find all pairs!")

    def win_level(self):
        self.status_label.setText("Level Complete!")
        self.parent.sound_manager.play_win()
        # If last level, show congrats dialog, else normal
        if self.level == TOTAL_LEVELS:
            self.parent.sound_manager.play_clap()
            dlg = CongratsDialog(self)
            dlg.exec_()
            self.parent.show_main_menu()
        else:
            QMessageBox.information(self, "Congrats!", f"You completed Level {self.level}!")
            self.parent.unlock_next_level(self.level)
            self.back_to_levels()

    def on_back(self):
        self.parent.sound_manager.play_button()
        self.parent.show_levels()

    def back_to_levels(self):
        self.parent.show_levels()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Matching Pics Game")
        self.showFullScreen()
        self.progress = load_progress()
        self.sound_manager = SoundManager()
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.menu = MainMenu(self)
        self.levels = LevelsPage(self, self.progress['unlocked_level'])
        self.game = None
        self.stack.addWidget(self.menu)
        self.stack.addWidget(self.levels)
        self.sound_manager.play_bg_music()
        self.show_main_menu()

    def show_main_menu(self):
        self.stack.setCurrentWidget(self.menu)

    def show_levels(self):
        self.levels.update_unlocks(self.progress["unlocked_level"])
        self.stack.setCurrentWidget(self.levels)

    def start_level(self, level):
        if self.game:
            self.stack.removeWidget(self.game)
            self.game.deleteLater()
        self.game = GamePage(self, level)
        self.stack.addWidget(self.game)
        self.stack.setCurrentWidget(self.game)

    def unlock_next_level(self, current_level):
        if current_level < TOTAL_LEVELS and self.progress['unlocked_level'] == current_level:
            self.progress['unlocked_level'] += 1
            save_progress(self.progress)
            self.levels.update_unlocks(self.progress["unlocked_level"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    Theme.apply(app)
    window = MainWindow()
    sys.exit(app.exec_())
