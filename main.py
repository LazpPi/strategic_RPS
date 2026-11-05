import pygame
import random
import sys
import os
import math
import serial
import serial.tools.list_ports
import platform

# ==========================================
# 1. M5StickCとのシリアル通信設定
# ==========================================
def find_m5stick_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.description.upper() or "USB" in port.device.upper():
            return port.device
    sys_name = platform.system()
    if sys_name == "Windows": return "COM3"
    elif sys_name == "Darwin": return "/dev/cu.usbserial-51526A2D93"
    else: return "/dev/ttyUSB0"

PORT = find_m5stick_port()
BAUD_RATE = 115200

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print(f"M5StickCと接続しました！ (ポート: {PORT})")
except Exception:
    ser = None
    print("M5StickCが見つかりません。ゲーム単体で起動します。")

def send_hand_to_m5(hand):
    if ser is None: return
    if hand == "グー": ser.write(b"G")
    elif hand == "チョキ": ser.write(b"C")
    elif hand == "パー": ser.write(b"P")


# ==========================================
# 2. Pygame・画面・フォントの初期設定
# ==========================================
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

# コントローラー設定
pygame.joystick.init()
joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"コントローラー接続: {joystick.get_name()}")
else:
    print("コントローラー未接続：キーボード操作で起動します")

def joy_button_pressed(button_number):
    return (joystick is not None and joystick.get_init() and 
            button_number < joystick.get_numbuttons() and joystick.get_button(button_number))

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("戦略的じゃんけん MVP")
clock = pygame.time.Clock()

# 色の定義
WHITE, BLACK, GRAY = (255, 255, 255), (30, 30, 30), (200, 200, 200)
DARK_GRAY = (100, 100, 100) # ★修正: メーター用のダークグレー
RED, GREEN, BLUE = (255, 100, 100), (100, 255, 100), (100, 100, 255)
ORANGE = (255, 150, 0)
YELLOW = (255, 220, 0)
LIGHT_RED, LIGHT_BLUE = (255, 200, 200), (200, 200, 255)
BROWN = (139, 69, 19) 

font_paths = [
    "/System/Library/Fonts/Hiragino Sans W4.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    "C:\\Windows\\Fonts\\meiryo.ttc",
    "C:\\Windows\\Fonts\\msgothic.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf"
]
jp_font_path = next((p for p in font_paths if os.path.exists(p)), None)
try:
    if jp_font_path:
        font = pygame.font.Font(jp_font_path, 24)
        large_font = pygame.font.Font(jp_font_path, 40)
        mid_font = pygame.font.Font(jp_font_path, 60)
        huge_font = pygame.font.Font(jp_font_path, 80)
    else:
        font_name = pygame.font.match_font(['hiraginosans', 'meiryo', 'msgothic', 'notosanscjkjp'])
        font = pygame.font.Font(font_name, 24)
        large_font = pygame.font.Font(font_name, 40)
        mid_font = pygame.font.Font(font_name, 60)
        huge_font = pygame.font.Font(font_name, 80)
except:
    font = large_font = mid_font = huge_font = pygame.font.Font(None, 40)


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
player_speed = 7
jump_speed = 16
gravity = 1

platforms = [
    pygame.Rect(100, 460, 150, 20),
    pygame.Rect(550, 460, 150, 20),
    pygame.Rect(325, 350, 150, 20)
]

hand_types = ["グー", "チョキ", "パー"]
ball_colors = {"グー": RED, "チョキ": GREEN, "パー": BLUE}
instructions = ["勝て", "負けろ", "あいこ"]

game_state = "HOME" 
play_count = 0      
clear_count = 0     
last_result = ""    
play_time = 60.0

def start_play():
    global hp, score, game_state, balls, player_x, player_y, velocity_y, is_jumping
    global robot_hand, current_inst, cycle_timer, play_count, play_time
    global invincible_timer 
    
    play_count += 1
    hp, score = 3, 0
    play_time = 60.0
    game_state = "PLAYING"
    balls = []
    invincible_timer = 0
    
    player_x, player_y = WIDTH // 2, HEIGHT - player_size - 20
    velocity_y, is_jumping = 0, False
    cycle_timer = 0
    
    robot_hand = random.choice(hand_types)
    current_inst = random.choice(instructions)
    send_hand_to_m5(robot_hand)
    print(f"ラウンド {play_count} 開始: 最初の手を「{robot_hand}」にセットして送信しました！")
    
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
    action_pressed = False 
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            action_pressed = True
        if event.type == pygame.JOYBUTTONDOWN and event.button in (0, 1, 2, 3, 4):
            action_pressed = True

    if action_pressed and game_state != "PLAYING":
        if game_state == "HOME":
            play_count = 0
            clear_count = 0
            start_play()
        elif game_state == "RESULT_RETRY":
            start_play()
        elif game_state == "RESULT_END":
            game_state = "HOME" 

    # ----------------------------------
    # 5.2 ロジック更新（プレイ中）
    # ----------------------------------
    if game_state == "PLAYING":
        play_time -= dt / 1000.0
        if play_time <= 0:
            play_time = 0

        if invincible_timer > 0:
            invincible_timer -= dt

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
        axis_x, axis_y, axis_4, axis_5 = 0.0, 0.0, -1.0, -1.0
        if joystick is not None and joystick.get_init():
            if joystick.get_numaxes() > 0: axis_x = joystick.get_axis(0)
            if joystick.get_numaxes() > 1: axis_y = joystick.get_axis(1)
            if joystick.get_numaxes() > 4: axis_4 = joystick.get_axis(4)
            if joystick.get_numaxes() > 5: axis_5 = joystick.get_axis(5)

        move_left = keys[pygame.K_LEFT] or joy_button_pressed(13) or axis_x <= -0.8
        move_right = keys[pygame.K_RIGHT] or joy_button_pressed(14) or axis_x >= 0.8
        if move_left and player_x > 0: player_x -= player_speed
        if move_right and player_x < WIDTH - player_size: player_x += player_speed

        jump_pressed = (keys[pygame.K_UP] or joy_button_pressed(11) or 
                        axis_y <= -0.5 or axis_4 >= 0.8 or axis_5 >= 0.8)
        
        if jump_pressed and not is_jumping:
            is_jumping = True
            velocity_y = -jump_speed
            play_sound(se_jump)

        down_pressed = keys[pygame.K_DOWN] or joy_button_pressed(12)

        if is_jumping:
            if down_pressed: velocity_y += 4
            player_y += velocity_y
            velocity_y += gravity
            
            if player_y >= HEIGHT - player_size - 20:
                player_y = HEIGHT - player_size - 20
                is_jumping = False
                velocity_y = 0
            else:
                if velocity_y > 0:
                    player_rect = pygame.Rect(player_x, player_y, player_size, player_size)
                    for plat in platforms:
                        if player_rect.colliderect(plat):
                            if player_rect.bottom - velocity_y <= plat.top + 15:
                                player_y = plat.top - player_size
                                is_jumping = False
                                velocity_y = 0
                                break
        else:
            if player_y < HEIGHT - player_size - 20:
                player_rect = pygame.Rect(player_x, player_y + 1, player_size, player_size)
                on_plat = False
                for plat in platforms:
                    if player_rect.colliderect(plat):
                        on_plat = True
                        break
                if not on_plat:
                    is_jumping = True 

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
                    balls.remove(ball)
                else:
                    # ★修正: 無敵判定を削除し、常にダメージを受けるように変更。点滅用のタイマーだけセットする
                    hp -= 1
                    play_sound(se_wrong)
                    invincible_timer = 1000 
                    balls.remove(ball)
            elif ball["rect"].y > HEIGHT:
                balls.remove(ball)

        if hp <= 0 or score >= 100 or play_time <= 0:
            if score >= 100:
                last_result = "CLEAR!"
                clear_count += 1
                play_sound(se_clear)
            elif hp <= 0:
                last_result = "GAME OVER"
            else:
                last_result = "TIME UP"
                
            pygame.mixer.music.stop()
            
            if play_count >= 3:
                game_state = "RESULT_END" 
            else:
                game_state = "RESULT_RETRY" 
    
    # ----------------------------------
    # 5.3 画面の描画
    # ----------------------------------
    if game_state == "PLAYING":
        if img_bg: screen.blit(img_bg, (0, 0))
        else: screen.fill(WHITE)
        
        for plat in platforms:
            pygame.draw.rect(screen, BROWN, plat)
            pygame.draw.rect(screen, BLACK, plat, 2) 

        screen.blit(font.render(f"{'♥' * hp}", True, RED), (10, 10))
        pygame.draw.rect(screen, GRAY, (10, 45, 200, 20))
        fill_width = min(200, int((score / 100) * 200))
        pygame.draw.rect(screen, ORANGE, (10, 45, fill_width, 20)) 
        pygame.draw.rect(screen, BLACK, (10, 45, 200, 20), 2)
        screen.blit(font.render("POINT", True, BLACK), (10, 70))

        time_str = str(math.ceil(play_time))
        scale = 1.0
        if play_time <= 10:
            scale = 1.0 + 0.3 * abs(math.sin(pygame.time.get_ticks() / 150.0))
        
        base_time_txt = huge_font.render(time_str, True, YELLOW)
        base_time_shadow = huge_font.render(time_str, True, BLACK)
        
        if scale != 1.0:
            base_time_txt = pygame.transform.rotozoom(base_time_txt, 0, scale)
            base_time_shadow = pygame.transform.rotozoom(base_time_shadow, 0, scale)
            
        time_rect = base_time_txt.get_rect(center=(WIDTH - 60, 50))
        shadow_rect = base_time_shadow.get_rect(center=(WIDTH - 60 + 3, 50 + 3))
        
        screen.blit(base_time_shadow, shadow_rect)
        screen.blit(base_time_txt, time_rect)


        # ==========================================
        # 統合UIパネルの描画
        # ==========================================
        ui_w, ui_h = 220, 155
        ui_x = WIDTH // 2 - ui_w // 2
        ui_y = 20
        
        ui_rect = pygame.Rect(ui_x, ui_y, ui_w, ui_h)
        # ★修正: 背景をダークグレーに変更
        pygame.draw.rect(screen, DARK_GRAY, ui_rect, border_top_left_radius=60, border_top_right_radius=60)
        pygame.draw.rect(screen, BLACK, ui_rect, 3, border_top_left_radius=60, border_top_right_radius=60)
        
        line_y = ui_y + 90
        pygame.draw.line(screen, BLACK, (ui_x, line_y), (ui_x + ui_w, line_y), 3)

        clock_r = 40
        inst_center = (WIDTH // 2 - 45, ui_y + 45)
        hand_center = (WIDTH // 2 + 45, ui_y + 45)
        
        # --- 左：指示タイマー ---
        pygame.draw.circle(screen, LIGHT_RED, inst_center, clock_r)
        pygame.draw.circle(screen, BLACK, inst_center, clock_r, 2)
        pygame.draw.line(screen, BLACK, (inst_center[0], inst_center[1] - clock_r), (inst_center[0], inst_center[1] - clock_r + 8), 3)
        
        inst_lbl = font.render("指示", True, (255, 130, 130))
        screen.blit(inst_lbl, (inst_center[0] - inst_lbl.get_width()//2, inst_center[1] - inst_lbl.get_height()//2))
        
        inst_angle = ((cycle_timer % 5000) / 5000.0) * 360
        rad_inst = math.radians(inst_angle)
        pygame.draw.line(screen, BLACK, inst_center, 
                         (inst_center[0] + clock_r * math.sin(rad_inst), inst_center[1] - clock_r * math.cos(rad_inst)), 3)

        # --- 右：手タイマー ---
        pygame.draw.circle(screen, LIGHT_BLUE, hand_center, clock_r)
        pygame.draw.circle(screen, BLACK, hand_center, clock_r, 2)
        pygame.draw.line(screen, BLACK, (hand_center[0], hand_center[1] - clock_r), (hand_center[0], hand_center[1] - clock_r + 8), 3)
        
        hand_lbl = font.render("手", True, (130, 130, 255))
        screen.blit(hand_lbl, (hand_center[0] - hand_lbl.get_width()//2, hand_center[1] - hand_lbl.get_height()//2))
        
        hand_angle = (cycle_timer / 10000.0) * 360
        rad_hand = math.radians(hand_angle)
        pygame.draw.line(screen, BLACK, hand_center, 
                         (hand_center[0] + clock_r * math.sin(rad_hand), hand_center[1] - clock_r * math.cos(rad_hand)), 3)

        # テキスト部
        inst_text = mid_font.render(current_inst, True, RED)
        inst_rect = inst_text.get_rect(center=(WIDTH//2, line_y + (ui_h - 90)//2))
        screen.blit(inst_text, inst_rect)

        # プレイヤーの描画（点滅演出）
        if invincible_timer <= 0 or (invincible_timer // 100) % 2 == 0:
            if img_player: screen.blit(img_player, (player_x, player_y))
            else: pygame.draw.rect(screen, BLACK, player_rect)

        for ball in balls:
            img = img_balls[ball["type"]]
            if img: screen.blit(img, (ball["rect"].x, ball["rect"].y))
            else: pygame.draw.ellipse(screen, ball["color"], ball["rect"])

    # === ホーム画面 ===
    elif game_state == "HOME":
        screen.fill(WHITE)
        title_text = huge_font.render("じゃんけんゲーム", True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 100))
        
        blink_str = "Aボタンでスタート" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))
            
        credit_text1 = font.render("背景素材: ゲームまてりあるず", True, GRAY)
        credit_text2 = font.render("https://game-materials.com/", True, GRAY)
        screen.blit(credit_text1, (WIDTH - credit_text1.get_width() - 10, HEIGHT - 70))
        screen.blit(credit_text2, (WIDTH - credit_text2.get_width() - 10, HEIGHT - 35))

    # === リトライ画面 ===
    elif game_state == "RESULT_RETRY":
        screen.fill(WHITE)
        round_str = f"{play_count + 1}nd round" if play_count == 1 else f"{play_count + 1}rd round"
        title_text = huge_font.render(round_str, True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 100))
        
        res_color = GREEN if last_result == "CLEAR!" else RED
        res_text = large_font.render(last_result, True, res_color)
        screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))

        blink_str = "Aボタンでスタート" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))

    # === 終了画面 ===
    elif game_state == "RESULT_END":
        screen.fill(WHITE)
        end_text = mid_font.render(f"{clear_count}回クリア！また遊んでね！", True, BLACK)
        screen.blit(end_text, (WIDTH//2 - end_text.get_width()//2, HEIGHT//2 - 50))
        
        blink_str = "Aボタンでホームに戻る" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))

    pygame.display.flip()
    clock.tick(60)

if ser is not None: ser.close()
if joystick is not None and joystick.get_init():
    joystick.quit()
pygame.quit()
sys.exit()