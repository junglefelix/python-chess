import pygame
import chess
import sys
import threading
import random

# --- Constants ---
WINDOW_SIZE   = 680
BOARD_SIZE    = 600
SQUARE_SIZE   = BOARD_SIZE // 8
BOARD_OFFSET_X = (WINDOW_SIZE - BOARD_SIZE) // 2
BOARD_OFFSET_Y = (WINDOW_SIZE - BOARD_SIZE) // 2
INFO_HEIGHT   = 40

# Colors
WHITE_SQUARE  = (240, 217, 181)
BLACK_SQUARE  = (181, 136,  99)
HIGHLIGHT_SEL = (100, 200, 100, 160)
HIGHLIGHT_MOV = (100, 180, 255, 140)
HIGHLIGHT_CHK = (220,  50,  50, 160)
BORDER_COLOR  = ( 80,  50,  30)
BG_COLOR      = ( 48,  46,  43)
TEXT_COLOR    = (240, 240, 230)
STATUS_COLOR  = (255, 215,   0)
BTN_COLOR     = ( 70,  90,  70)
BTN_HOVER     = (100, 140, 100)
BTN_TEXT      = (240, 240, 210)

# Unicode chess pieces  (white, black)
PIECE_UNICODE = {
    (chess.KING,   chess.WHITE): "♔",
    (chess.QUEEN,  chess.WHITE): "♕",
    (chess.ROOK,   chess.WHITE): "♖",
    (chess.BISHOP, chess.WHITE): "♗",
    (chess.KNIGHT, chess.WHITE): "♘",
    (chess.PAWN,   chess.WHITE): "♙",
    (chess.KING,   chess.BLACK): "♚",
    (chess.QUEEN,  chess.BLACK): "♛",
    (chess.ROOK,   chess.BLACK): "♜",
    (chess.BISHOP, chess.BLACK): "♝",
    (chess.KNIGHT, chess.BLACK): "♞",
    (chess.PAWN,   chess.BLACK): "♟",
}

# --- AI ---
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:  20000,
}

# Piece-square tables (from White perspective, rank 0 = White back rank)
PST = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    chess.ROOK: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    chess.KING: [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ],
}


def pst_value(piece_type, sq, color):
    table = PST.get(piece_type, [0] * 64)
    idx = sq if color == chess.WHITE else chess.square_mirror(sq)
    return table[idx]


def evaluate_board(board):
    if board.is_checkmate():
        return -100000 if board.turn == chess.WHITE else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        val = PIECE_VALUES[piece.piece_type] + pst_value(piece.piece_type, sq, piece.color)
        score += val if piece.color == chess.WHITE else -val
    return score


def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)
    if maximizing:
        best = -10000000
        for move in board.legal_moves:
            board.push(move)
            best = max(best, minimax(board, depth - 1, alpha, beta, False))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 10000000
        for move in board.legal_moves:
            board.push(move)
            best = min(best, minimax(board, depth - 1, alpha, beta, True))
            board.pop()
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


# Difficulty 1-9: (search_depth, random_move_chance)
# Low difficulty = shallow search + high chance of picking a random legal move
DIFFICULTY_SETTINGS = {
    1: (1, 0.90),
    2: (1, 0.65),
    3: (1, 0.30),
    4: (2, 0.08),
    5: (3, 0.0),
    6: (3, 0.0),
    7: (4, 0.0),
    8: (4, 0.0),
    9: (5, 0.0),
}

DIFFICULTY_LABELS = {
    1: "Beginner",
    2: "Very Easy",
    3: "Easy",
    4: "Casual",
    5: "Medium",
    6: "Hard",
    7: "Expert",
    8: "Master",
    9: "Impossible",
}


def get_ai_move(board, depth=3, random_chance=0.0):
    moves = list(board.legal_moves)
    if not moves:
        return None
    if random_chance > 0 and random.random() < random_chance:
        return random.choice(moves)
    random.shuffle(moves)
    maximizing_root = board.turn == chess.WHITE
    best_move = moves[0]
    best_val = -10000000 if maximizing_root else 10000000
    for move in moves:
        board.push(move)
        val = minimax(board, depth - 1, -10000000, 10000000, not maximizing_root)
        board.pop()
        if maximizing_root:
            if val > best_val:
                best_val = val
                best_move = move
        else:
            if val < best_val:
                best_val = val
                best_move = move
    return best_move


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def square_to_screen(sq, flipped=False):
    col = chess.square_file(sq)
    row = chess.square_rank(sq)
    if not flipped:
        row = 7 - row
    return (
        BOARD_OFFSET_X + col * SQUARE_SIZE,
        BOARD_OFFSET_Y + row * SQUARE_SIZE,
    )


def screen_to_square(px, py, flipped=False):
    col = (px - BOARD_OFFSET_X) // SQUARE_SIZE
    row = (py - BOARD_OFFSET_Y) // SQUARE_SIZE
    if not (0 <= col < 8 and 0 <= row < 8):
        return None
    rank = row if flipped else 7 - row
    return chess.square(col, rank)


# ---------------------------------------------------------------------------
# Main game class
# ---------------------------------------------------------------------------

class ChessGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE + INFO_HEIGHT))
        pygame.display.set_caption("Chess — python-chess + pygame")

        self.piece_font  = self._load_unicode_font(int(SQUARE_SIZE * 0.72))
        self.label_font  = pygame.font.SysFont("segoeui", 16)
        self.status_font = pygame.font.SysFont("segoeui", 18, bold=True)
        self.title_font  = pygame.font.SysFont("segoeui", 52, bold=True)
        self.btn_font    = pygame.font.SysFont("segoeui", 26, bold=True)

        self.overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)

        self.board         = chess.Board()
        self.selected_sq   = None
        self.legal_targets = set()
        self.flipped       = False
        self.game_over_msg = ""
        self.vs_computer   = False
        self.ai_color      = chess.BLACK
        self.ai_difficulty = 5
        self.ai_thinking   = False
        self._ai_result    = None
        self._ai_thread    = None

    # ------------------------------------------------------------------
    @staticmethod
    def _load_unicode_font(size):
        candidates = [
            "segoeuisymbol", "seguisym",
            "dejavusans", "notosans",
            "freesans", "liberationsans",
            "arial", "symbola",
        ]
        for name in candidates:
            try:
                fnt = pygame.font.SysFont(name, size)
                surf = fnt.render("♔", True, (0, 0, 0))
                if surf.get_width() > 4:
                    return fnt
            except Exception:
                pass
        return pygame.font.Font(None, size)

    # ------------------------------------------------------------------
    # Menu screen
    # ------------------------------------------------------------------
    def show_menu(self):
        """Returns (vs_computer: bool, difficulty: int or None)."""
        btn_w, btn_h = 300, 60
        btn_x = WINDOW_SIZE // 2 - btn_w // 2
        btn_2p  = pygame.Rect(btn_x, 340, btn_w, btn_h)
        btn_cpu = pygame.Rect(btn_x, 430, btn_w, btn_h)
        clock = pygame.time.Clock()
        while True:
            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_2p.collidepoint(mx, my):
                        return False, None
                    if btn_cpu.collidepoint(mx, my):
                        diff = self.show_difficulty_menu()
                        return True, diff

            self.screen.fill(BG_COLOR)

            title_surf = self.title_font.render("CHESS", True, STATUS_COLOR)
            self.screen.blit(title_surf, title_surf.get_rect(center=(WINDOW_SIZE // 2, 180)))

            sub = self.label_font.render("Choose a game mode", True, TEXT_COLOR)
            self.screen.blit(sub, sub.get_rect(center=(WINDOW_SIZE // 2, 260)))

            deco = self.piece_font.render("♙  ♟", True, (160, 130, 90))
            self.screen.blit(deco, deco.get_rect(center=(WINDOW_SIZE // 2, 305)))

            for rect, label in [(btn_2p, "2 Players"), (btn_cpu, "vs Computer  (AI)")]:
                hover = rect.collidepoint(mx, my)
                pygame.draw.rect(self.screen, BTN_HOVER if hover else BTN_COLOR, rect, border_radius=10)
                pygame.draw.rect(self.screen, STATUS_COLOR, rect, 2, border_radius=10)
                t = self.btn_font.render(label, True, BTN_TEXT)
                self.screen.blit(t, t.get_rect(center=rect.center))

            hint = self.label_font.render(
                "R = menu   F = flip board   U = undo   Esc = quit", True, (140, 140, 130)
            )
            self.screen.blit(hint, hint.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE + INFO_HEIGHT // 2)))

            pygame.display.flip()
            clock.tick(60)

    def show_difficulty_menu(self):
        """Returns chosen difficulty 1-9."""
        # 3x3 grid of difficulty buttons
        btn_w, btn_h = 180, 58
        cols, rows = 3, 3
        grid_w = cols * btn_w + (cols - 1) * 12
        grid_x = WINDOW_SIZE // 2 - grid_w // 2
        grid_y = 260
        cell_step_x = btn_w + 12
        cell_step_y = btn_h + 12

        diff_rects = {}
        for i, level in enumerate(range(1, 10)):
            col = i % cols
            row = i // cols
            rect = pygame.Rect(
                grid_x + col * cell_step_x,
                grid_y + row * cell_step_y,
                btn_w, btn_h,
            )
            diff_rects[level] = rect

        back_rect = pygame.Rect(WINDOW_SIZE // 2 - 100, grid_y + 3 * cell_step_y + 10, 200, 46)
        clock = pygame.time.Clock()
        selected = 5  # highlighted level

        # colours per difficulty band
        def level_color(lvl, hover):
            if lvl <= 3:
                base = (60, 100, 60) if not hover else (80, 140, 80)
            elif lvl <= 6:
                base = (90, 80, 40) if not hover else (130, 115, 55)
            else:
                base = (110, 45, 45) if not hover else (155, 65, 65)
            return base

        while True:
            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return selected
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for lvl, rect in diff_rects.items():
                        if rect.collidepoint(mx, my):
                            return lvl
                    if back_rect.collidepoint(mx, my):
                        return selected

            self.screen.fill(BG_COLOR)

            title_surf = self.title_font.render("DIFFICULTY", True, STATUS_COLOR)
            self.screen.blit(title_surf, title_surf.get_rect(center=(WINDOW_SIZE // 2, 120)))

            sub = self.label_font.render("Choose how hard the computer plays", True, TEXT_COLOR)
            self.screen.blit(sub, sub.get_rect(center=(WINDOW_SIZE // 2, 195)))

            sub2 = self.label_font.render(
                "1 = very easy  /  9 = impossible", True, (160, 150, 130)
            )
            self.screen.blit(sub2, sub2.get_rect(center=(WINDOW_SIZE // 2, 220)))

            for lvl, rect in diff_rects.items():
                hover = rect.collidepoint(mx, my)
                color = level_color(lvl, hover)
                pygame.draw.rect(self.screen, color, rect, border_radius=8)
                border_col = STATUS_COLOR if hover else (160, 140, 80)
                pygame.draw.rect(self.screen, border_col, rect, 2, border_radius=8)
                num_surf = self.btn_font.render(str(lvl), True, STATUS_COLOR)
                lbl_surf = self.label_font.render(DIFFICULTY_LABELS[lvl], True, BTN_TEXT)
                self.screen.blit(num_surf, num_surf.get_rect(
                    centerx=rect.centerx, top=rect.top + 6))
                self.screen.blit(lbl_surf, lbl_surf.get_rect(
                    centerx=rect.centerx, bottom=rect.bottom - 6))

            hover_back = back_rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, BTN_HOVER if hover_back else BTN_COLOR, back_rect, border_radius=8)
            pygame.draw.rect(self.screen, STATUS_COLOR, back_rect, 2, border_radius=8)
            back_surf = self.label_font.render("← Back", True, BTN_TEXT)
            self.screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))

            hint = self.label_font.render(
                "R = menu   F = flip board   U = undo   Esc = quit", True, (140, 140, 130)
            )
            self.screen.blit(hint, hint.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE + INFO_HEIGHT // 2)))

            pygame.display.flip()
            clock.tick(60)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw_board(self):
        for rank in range(8):
            for file in range(8):
                sq = chess.square(file, 7 - rank) if not self.flipped else chess.square(file, rank)
                color = WHITE_SQUARE if (file + rank) % 2 == 0 else BLACK_SQUARE
                rect = pygame.Rect(
                    BOARD_OFFSET_X + file * SQUARE_SIZE,
                    BOARD_OFFSET_Y + rank * SQUARE_SIZE,
                    SQUARE_SIZE, SQUARE_SIZE,
                )
                pygame.draw.rect(self.screen, color, rect)

                if self.board.is_check():
                    king_sq = self.board.king(self.board.turn)
                    if sq == king_sq:
                        self.overlay.fill((0, 0, 0, 0))
                        pygame.draw.rect(self.overlay, HIGHLIGHT_CHK, (0, 0, SQUARE_SIZE, SQUARE_SIZE))
                        self.screen.blit(self.overlay, rect.topleft)

                if sq == self.selected_sq:
                    self.overlay.fill((0, 0, 0, 0))
                    pygame.draw.rect(self.overlay, HIGHLIGHT_SEL, (0, 0, SQUARE_SIZE, SQUARE_SIZE))
                    self.screen.blit(self.overlay, rect.topleft)

                if sq in self.legal_targets:
                    self.overlay.fill((0, 0, 0, 0))
                    center = (SQUARE_SIZE // 2, SQUARE_SIZE // 2)
                    if self.board.piece_at(sq):
                        pygame.draw.circle(self.overlay, HIGHLIGHT_MOV, center, SQUARE_SIZE // 2 - 4, 6)
                    else:
                        pygame.draw.circle(self.overlay, HIGHLIGHT_MOV, center, SQUARE_SIZE // 7)
                    self.screen.blit(self.overlay, rect.topleft)

    def draw_pieces(self):
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece is None:
                continue
            glyph        = PIECE_UNICODE[(piece.piece_type, piece.color)]
            color        = (255, 255, 255) if piece.color == chess.WHITE else (20, 20, 20)
            shadow_color = (30, 30, 30)    if piece.color == chess.WHITE else (180, 180, 180)
            sx, sy = square_to_screen(sq, self.flipped)
            cx = sx + SQUARE_SIZE // 2
            cy = sy + SQUARE_SIZE // 2
            surf = self.piece_font.render(glyph, True, shadow_color)
            self.screen.blit(surf, surf.get_rect(center=(cx + 2, cy + 2)))
            surf = self.piece_font.render(glyph, True, color)
            self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def draw_coordinates(self):
        files = "abcdefgh"
        ranks = "12345678"
        for i in range(8):
            f_char = files[i] if not self.flipped else files[7 - i]
            surf = self.label_font.render(f_char, True, TEXT_COLOR)
            self.screen.blit(surf, (
                BOARD_OFFSET_X + i * SQUARE_SIZE + SQUARE_SIZE - surf.get_width() - 3,
                BOARD_OFFSET_Y + BOARD_SIZE - surf.get_height() - 3,
            ))
            r_char = ranks[7 - i] if not self.flipped else ranks[i]
            surf = self.label_font.render(r_char, True, TEXT_COLOR)
            self.screen.blit(surf, (
                BOARD_OFFSET_X + 3,
                BOARD_OFFSET_Y + i * SQUARE_SIZE + 3,
            ))

    def draw_border(self):
        pygame.draw.rect(
            self.screen, BORDER_COLOR,
            (BOARD_OFFSET_X - 3, BOARD_OFFSET_Y - 3, BOARD_SIZE + 6, BOARD_SIZE + 6),
            3,
        )

    def draw_status(self):
        bar_rect = pygame.Rect(0, WINDOW_SIZE, WINDOW_SIZE, INFO_HEIGHT)
        pygame.draw.rect(self.screen, (30, 28, 26), bar_rect)

        mode_tag = "  [vs CPU]" if self.vs_computer else "  [2P]"

        if self.game_over_msg:
            msg   = self.game_over_msg
            color = STATUS_COLOR
        elif self.ai_thinking:
            lbl = DIFFICULTY_LABELS.get(self.ai_difficulty, "")
            msg   = f"Computer is thinking...  [{self.ai_difficulty} - {lbl}]"
            color = (180, 180, 255)
        elif self.board.is_check():
            turn  = "White" if self.board.turn == chess.WHITE else "Black"
            msg   = f"{turn} is in CHECK!{mode_tag}"
            color = (255, 100, 100)
        else:
            turn     = "White" if self.board.turn == chess.WHITE else "Black"
            move_num = self.board.fullmove_number
            diff_tag = f"  Lvl {self.ai_difficulty}" if self.vs_computer else ""
            msg   = f"Move {move_num}  -  {turn} to move{mode_tag}{diff_tag}    F=flip  R=menu  U=undo"
            color = TEXT_COLOR

        surf = self.status_font.render(msg, True, color)
        self.screen.blit(surf, surf.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE + INFO_HEIGHT // 2)))

    def render(self):
        self.screen.fill(BG_COLOR)
        self.draw_board()
        self.draw_pieces()
        self.draw_coordinates()
        self.draw_border()
        self.draw_status()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------
    def handle_click(self, px, py):
        if self.game_over_msg or self.ai_thinking:
            return
        if self.vs_computer and self.board.turn == self.ai_color:
            return

        sq = screen_to_square(px, py, self.flipped)
        if sq is None:
            self.deselect()
            return

        if self.selected_sq is not None:
            move = chess.Move(self.selected_sq, sq)
            piece = self.board.piece_at(self.selected_sq)
            if (
                piece is not None
                and piece.piece_type == chess.PAWN
                and chess.square_rank(sq) in (0, 7)
            ):
                move = chess.Move(self.selected_sq, sq, promotion=chess.QUEEN)

            if move in self.board.legal_moves:
                self.board.push(move)
                self.deselect()
                self.check_game_over()
                if not self.game_over_msg and self.vs_computer and self.board.turn == self.ai_color:
                    self.start_ai()
                return

            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn:
                self.select(sq)
                return
            self.deselect()
            return

        piece = self.board.piece_at(sq)
        if piece and piece.color == self.board.turn:
            self.select(sq)

    def select(self, sq):
        self.selected_sq   = sq
        self.legal_targets = {m.to_square for m in self.board.legal_moves if m.from_square == sq}

    def deselect(self):
        self.selected_sq   = None
        self.legal_targets = set()

    def check_game_over(self):
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            self.game_over_msg = f"Checkmate! {winner} wins!  [R] for menu"
        elif self.board.is_stalemate():
            self.game_over_msg = "Stalemate — Draw!  [R] for menu"
        elif self.board.is_insufficient_material():
            self.game_over_msg = "Insufficient material — Draw!  [R] for menu"
        elif self.board.is_seventyfive_moves():
            self.game_over_msg = "75-move rule — Draw!  [R] for menu"
        elif self.board.is_fivefold_repetition():
            self.game_over_msg = "Fivefold repetition — Draw!  [R] for menu"

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------
    def start_ai(self):
        self.ai_thinking = True
        self._ai_result  = None
        board_copy       = self.board.copy()

        def worker():
            depth, rand_chance = DIFFICULTY_SETTINGS.get(self.ai_difficulty, (3, 0.0))
            self._ai_result = get_ai_move(board_copy, depth=depth, random_chance=rand_chance)

        self._ai_thread = threading.Thread(target=worker, daemon=True)
        self._ai_thread.start()

    def poll_ai(self):
        if not self.ai_thinking:
            return
        if self._ai_thread and not self._ai_thread.is_alive():
            self.ai_thinking = False
            if self._ai_result and self._ai_result in self.board.legal_moves:
                self.board.push(self._ai_result)
                self.check_game_over()

    # ------------------------------------------------------------------
    # Game management
    # ------------------------------------------------------------------
    def new_game(self, vs_computer, difficulty=5):
        self.vs_computer   = vs_computer
        self.ai_difficulty = difficulty if difficulty is not None else 5
        self.board         = chess.Board()
        self.deselect()
        self.game_over_msg = ""
        self.ai_thinking   = False
        self._ai_result    = None
        self.flipped       = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        clock = pygame.time.Clock()

        vs_cpu, difficulty = self.show_menu()
        self.new_game(vs_cpu, difficulty)

        while True:
            self.poll_ai()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(*event.pos)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        vs_cpu, difficulty = self.show_menu()
                        self.new_game(vs_cpu, difficulty)
                    elif event.key == pygame.K_f:
                        self.flipped = not self.flipped
                    elif event.key == pygame.K_u:
                        if not self.game_over_msg and not self.ai_thinking and self.board.move_stack:
                            self.board.pop()
                            if self.vs_computer and self.board.move_stack:
                                self.board.pop()
                            self.deselect()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            self.render()
            clock.tick(60)


if __name__ == "__main__":
    ChessGame().run()
