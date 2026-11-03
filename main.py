import pygame
import random
import sys
import os
import math
import serial
import serial.tools.list_ports # ポート自動検出用
import platform                # OS判別用

# ==========================================
# 1. M5StickCとのシリアル通信設定（OS自動判別）
# ==========================================
def find_m5stick_port():
    """OSを問わず、接続されているUSBシリアルポートを自動検索する"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # 説明文やデバイス名に「USB」が含まれるポートをM5StickCとみなす
        if "USB" in port.description.upper() or "USB" in port.device.upper():
            return port.device
    
    # 自動検出で見つからなかった場合の各OSのデフォルト候補（保険）
    sys_name = platform.system()
    if sys_name == "Windows": return "COM3"
    elif sys_name == "Darwin": return "/dev/cu.usbserial-51526A2D93" # Mac
    else: return "/dev/ttyUSB0" # Raspberry Pi / Linux

PORT = find_m5stick_port()
BAUD_RATE = 115200

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print(f"M5StickCと接続しました！ (ポート: {PORT})")
except Exception:
    ser = None
    print("M5StickCが見つかりません。ゲーム単体で起動します。")

def send_hand_to_m5(hand):
    """M5StickCへ手の形（G/C/P）を送信する"""
    if ser is None: return
    if hand == "グー": ser.write(b"G")
    elif hand == "チョキ": ser.write(b"C")
    elif hand == "パー": ser.write(b"P")


# ==========================================
# 2. Pygame・画面・フォントの初期設定（全OS対応）
# ==========================================
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("戦略的じゃんけん MVP")
clock = pygame.time.Clock()

WHITE, BLACK, GRAY = (255, 255, 255), (30, 30, 30), (200, 200, 200)
RED, GREEN, BLUE = (255, 100, 100), (100, 255, 100), (100, 100, 255)
LIGHT_RED, LIGHT_BLUE = (255, 200, 200), (200, 200, 255)

# Mac / Windows / Raspberry Pi の各日本語フォントパス候補
font_paths = [
    "/System/Library/Fonts/Hiragino Sans W4.ttc", # Mac
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc", # Mac
    "C:\\Windows\\Fonts\\meiryo.ttc", # Windows
    "C:\\Windows\\Fonts\\msgothic.ttc", # Windows
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", # Raspberry Pi
    "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf" # Linux汎用
]
jp_font_path = next((p for p in font_paths if os.path.exists(p)), None)
try:
    if jp_font_path:
        font = pygame.font.Font(jp_font_path, 24)
        large_font = pygame.font.Font(jp_font_path, 40)
        huge_font = pygame.font.Font(jp_font_path, 80)
    else:
        # 見つからない場合はPygameに各OSのフォント名で探させる
        font_name = pygame.font.match_font(['hiraginosans', 'meiryo', 'msgothic', 'notosanscjkjp'])
        font = pygame.font.Font(font_name, 24)
        large_font = pygame.font.Font(font_name, 40)
        huge_font = pygame.font.Font(font_name, 80)
except:
    font = large_font = huge_font = pygame.font.Font(None, 40)


# ==========================================
# 3. 素材（画像・音声）の読み込み
# ==========================================
player_size, ball_size = 50, 60

def load_image(filename, size):
    filepath = os.path.join("images", filename)
    if os.path.exists(filepath):
        return pygame.transform.scale(pygame.image.load(filepath).convert_alpha(), size)
    return None

def load_sound(filename):
    filepath = os.path.join("sounds", filename)
    if os.path.exists(filepath):
        return pygame.mixer.Sound(filepath)
    return None

def play_sound(sound):
    if sound: sound.play()

img_player = load_image("player.png", (player_size, player_size))
img_balls = {
    "グー": load_image("rock.png", (ball_size, ball_size)),
    "チョキ": load_image("scissors.png", (ball_size, ball_size)),
    "パー": load_image("paper.png", (ball_size, ball_size))
}
img_bg = load_image("bg.jpg", (WIDTH, HEIGHT))

se_jump = load_sound("jump.mp3")
se_correct = load_sound("correct.mp3")
se_wrong = load_sound("wrong.mp3")
se_inst_change = load_sound("count.mp3") 
se_hand_change = load_sound("count.mp3") 
se_clear = load_sound("clear.mp3")

bgm_path = os.path.join("sounds", "bgm.mp3")
if os.path.exists(bgm_path):
    pygame.mixer.music.load(bgm_path)
    pygame.mixer.music.set_volume(0.5)


# ==========================================
# 4. ゲームルールの設定と関数
# ==========================================
player_speed, jump_speed, gravity = 7, 16, 1
hand_types = ["グー", "チョキ", "パー"]
ball_colors = {"グー": RED, "チョキ": GREEN, "パー": BLUE}
instructions = ["勝て", "負けろ", "あいこ"]

game_state = "TITLE" 

def reset_game():
    global hp, score, game_state, balls, player_x, player_y, velocity_y, is_jumping
    global robot_hand, current_inst, cycle_timer
    
    hp, score = 3, 0
    game_state = "PLAYING"
    balls = []
    
    player_x, player_y = WIDTH // 2, HEIGHT - player_size - 20
    velocity_y, is_jumping = 0, False
    cycle_timer = 0
    
    robot_hand = random.choice(hand_types)
    current_inst = random.choice(instructions)
    send_hand_to_m5(robot_hand)
    print(f"ゲーム開始: 最初の手を「{robot_hand}」にセットして送信しました！")
    
    if os.path.exists(bgm_path):
        pygame.mixer.music.play(-1)

def spawn_ball():
    b_type = random.choice(hand_types)
    x = random.randint(50, WIDTH - 50)
    balls.append({"rect": pygame.Rect(x, -50, ball_size, ball_size), "type": b_type, "color": ball_colors[b_type]})

def get_correct_hand(robot, inst):
    if inst == "あいこ": return robot
    elif inst == "勝て": return {"グー": "パー", "チョキ": "グー", "パー": "チョキ"}[robot]
    elif inst == "負けろ": return {"グー": "チョキ", "チョキ": "パー", "パー": "グー"}[robot]


# ==========================================
# 5. メインループ
# ==========================================
last_tick = pygame.time.get_ticks()
spawn_timer = 0
running = True

while running:
    current_tick = pygame.time.get_ticks()
    dt = current_tick - last_tick
    last_tick = current_tick

    # ----------------------------------
    # 5.1 イベント処理
    # ----------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and game_state != "PLAYING":
                reset_game()

    # ----------------------------------
    # 5.2 ロジック更新
    # ----------------------------------
    if game_state == "PLAYING":
        old_timer = cycle_timer
        cycle_timer += dt
        
        if old_timer < 5000 and cycle_timer >= 5000:
            current_inst = random.choice(instructions)
            play_sound(se_inst_change) 
        
        if cycle_timer >= 10000:
            cycle_timer -= 10000
            robot_hand = random.choice(hand_types)
            send_hand_to_m5(robot_hand)
            play_sound(se_hand_change) 

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player_x > 0: 
            player_x -= player_speed
        if keys[pygame.K_RIGHT] and player_x < WIDTH - player_size: 
            player_x += player_speed
        if keys[pygame.K_UP] and not is_jumping:
            is_jumping = True
            velocity_y = -jump_speed
            play_sound(se_jump)

        if is_jumping:
            if keys[pygame.K_DOWN]: velocity_y += 4
            player_y += velocity_y
            velocity_y += gravity
            if player_y >= HEIGHT - player_size - 20:
                player_y, is_jumping, velocity_y = HEIGHT - player_size - 20, False, 0

        spawn_timer += dt
        if spawn_timer > 1000:
            spawn_ball()
            spawn_timer = 0

        player_rect = pygame.Rect(player_x, player_y, player_size, player_size)
        correct_hand = get_correct_hand(robot_hand, current_inst)

        for ball in balls[:]:
            ball["rect"].y += 5
            if player_rect.colliderect(ball["rect"]):
                if ball["type"] == correct_hand:
                    score += 10
                    play_sound(se_correct)
                else:
                    hp -= 1
                    play_sound(se_wrong)
                balls.remove(ball)
            elif ball["rect"].y > HEIGHT:
                balls.remove(ball)

        if hp <= 0: 
            game_state = "LOSE"
            pygame.mixer.music.stop()
        elif score >= 100: 
            game_state = "WIN"
            pygame.mixer.music.stop()
            play_sound(se_clear)
    
    # ----------------------------------
    # 5.3 画面の描画
    # ----------------------------------
    if game_state == "PLAYING":
        if img_bg: screen.blit(img_bg, (0, 0))
        else: screen.fill(WHITE)

        screen.blit(font.render(f"HP: {'♥' * hp}", True, RED), (10, 10))
        pygame.draw.rect(screen, GRAY, (10, 45, 200, 20))
        fill_width = min(200, int((score / 100) * 200))
        pygame.draw.rect(screen, GREEN, (10, 45, fill_width, 20))
        pygame.draw.rect(screen, BLACK, (10, 45, 200, 20), 2)
        screen.blit(font.render("POINT", True, BLACK), (10, 70))

        clock_center = (WIDTH // 2, 70)
        clock_r = 45
        pygame.draw.circle(screen, LIGHT_RED, clock_center, clock_r, draw_top_right=True, draw_bottom_right=True)
        pygame.draw.circle(screen, LIGHT_BLUE, clock_center, clock_r, draw_top_left=True, draw_bottom_left=True)
        pygame.draw.circle(screen, BLACK, clock_center, clock_r, 2)
        
        screen.blit(font.render("手", True, BLUE), (clock_center[0] - 80, clock_center[1] - 15))
        screen.blit(font.render("指示", True, RED), (clock_center[0] + 55, clock_center[1] - 15))

        angle = (cycle_timer / 10000.0) * 360
        rad = math.radians(angle)
        needle_x = clock_center[0] + clock_r * math.sin(rad)
        needle_y = clock_center[1] - clock_r * math.cos(rad)
        pygame.draw.line(screen, BLACK, clock_center, (needle_x, needle_y), 3)

        inst_text = huge_font.render(current_inst, True, RED)
        screen.blit(inst_text, (WIDTH//2 - inst_text.get_width()//2, 130))

        if img_player: screen.blit(img_player, (player_x, player_y))
        else: pygame.draw.rect(screen, BLACK, player_rect)

        for ball in balls:
            img = img_balls[ball["type"]]
            if img: screen.blit(img, (ball["rect"].x, ball["rect"].y))
            else: pygame.draw.ellipse(screen, ball["color"], ball["rect"])

    else:
        screen.fill(WHITE)
        title_text = huge_font.render("じゃんけんゲーム", True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 100))
        
        if game_state == "WIN":
            res_text = large_font.render("CLEAR!", True, GREEN)
            screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))
        elif game_state == "LOSE":
            res_text = large_font.render("GAME OVER", True, RED)
            screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))

        blink_str = "Press SPACE to Play" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))

        credit_text1 = font.render("背景素材: ゲームまてりあるず", True, GRAY)
        credit_text2 = font.render("https://game-materials.com/", True, GRAY)
        screen.blit(credit_text1, (WIDTH - credit_text1.get_width() - 10, HEIGHT - 70))
        screen.blit(credit_text2, (WIDTH - credit_text2.get_width() - 10, HEIGHT - 35))

    pygame.display.flip()
    clock.tick(60)

if ser is not None: ser.close()
pygame.quit()
sys.exit()