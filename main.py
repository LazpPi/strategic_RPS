import pygame
import random
import sys
import os
import math
import serial

# ==========================================
# 1. M5StickCとのシリアル通信設定
# ==========================================
PORT = "/dev/cu.usbserial-51526A2D93" 
BAUD_RATE = 115200

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print("M5StickCと接続しました！")
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
# 2. Pygame・画面・フォントの初期設定
# ==========================================
pygame.mixer.pre_init(44100, -16, 2, 512) # 音ズレ防止
pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("戦略的じゃんけん MVP")
clock = pygame.time.Clock()

# 色の定義
WHITE, BLACK, GRAY = (255, 255, 255), (30, 30, 30), (200, 200, 200)
RED, GREEN, BLUE = (255, 100, 100), (100, 255, 100), (100, 100, 255)
LIGHT_RED, LIGHT_BLUE = (255, 200, 200), (200, 200, 255)

# Mac/Windows対応の日本語フォント自動探索
font_paths = [
    "/System/Library/Fonts/Hiragino Sans W4.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf"
]
jp_font_path = next((p for p in font_paths if os.path.exists(p)), None)
try:
    if jp_font_path:
        font = pygame.font.Font(jp_font_path, 24)
        large_font = pygame.font.Font(jp_font_path, 40)
        huge_font = pygame.font.Font(jp_font_path, 80)
    else:
        font_name = pygame.font.match_font(['hiraginosans', 'applegothic'])
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
    """imagesフォルダから画像を読み込み、サイズを調整する"""
    filepath = os.path.join("images", filename)
    if os.path.exists(filepath):
        return pygame.transform.scale(pygame.image.load(filepath).convert_alpha(), size)
    return None

def load_sound(filename):
    """soundsフォルダから効果音を読み込む"""
    filepath = os.path.join("sounds", filename)
    if os.path.exists(filepath):
        return pygame.mixer.Sound(filepath)
    return None

def play_sound(sound):
    """音が設定されていれば鳴らす"""
    if sound: sound.play()

# 画像ファイル
img_player = load_image("player.png", (player_size, player_size))
img_balls = {
    "グー": load_image("rock.png", (ball_size, ball_size)),
    "チョキ": load_image("scissors.png", (ball_size, ball_size)),
    "パー": load_image("paper.png", (ball_size, ball_size))
}
img_bg = load_image("bg.jpg", (WIDTH, HEIGHT))

# 効果音ファイル
se_jump = load_sound("jump.mp3")
se_correct = load_sound("correct.mp3")
se_wrong = load_sound("wrong.mp3")
se_inst_change = load_sound("count.mp3") 
se_hand_change = load_sound("count.mp3") 
se_clear = load_sound("clear.mp3")

# BGMの設定
bgm_path = os.path.join("sounds", "bgm.mp3")
if os.path.exists(bgm_path):
    pygame.mixer.music.load(bgm_path)
    pygame.mixer.music.set_volume(0.5)


# ==========================================
# 4. ゲームルールの設定と関数
# ==========================================
player_speed, jump_speed, gravity = 7, 16, 1
hand_types = ["グー", "チョキ", "パー"]
ball_colors = {"グー": RED, "チョキ": GREEN, "パー": BLUE} # 画像がない時の代替色
instructions = ["勝て", "負けろ", "あいこ"]

# 初期ステータス
game_state = "TITLE" # TITLE, PLAYING, WIN, LOSE

def reset_game():
    """ゲーム開始・リトライ時に変数を初期化する"""
    global hp, score, game_state, balls, player_x, player_y, velocity_y, is_jumping
    global robot_hand, current_inst, cycle_timer
    
    hp, score = 3, 0
    game_state = "PLAYING"
    balls = []
    
    # プレイヤーの初期位置
    player_x, player_y = WIDTH // 2, HEIGHT - player_size - 20
    velocity_y, is_jumping = 0, False
    cycle_timer = 0
    
    # 最初の手と指示をセットし、ロボットへ送信
    robot_hand = random.choice(hand_types)
    current_inst = random.choice(instructions)
    send_hand_to_m5(robot_hand)
    print(f"ゲーム開始: 最初の手を「{robot_hand}」にセットして送信しました！")
    
    if os.path.exists(bgm_path):
        pygame.mixer.music.play(-1) # BGMループ再生

def spawn_ball():
    """画面上部からランダムなボールを降らせる"""
    b_type = random.choice(hand_types)
    x = random.randint(50, WIDTH - 50)
    balls.append({"rect": pygame.Rect(x, -50, ball_size, ball_size), "type": b_type, "color": ball_colors[b_type]})

def get_correct_hand(robot, inst):
    """ロボットの手と指示から、キャッチすべき正解の手を判定する"""
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
    # 経過時間の計算（dt: 前回フレームからの経過ミリ秒）
    current_tick = pygame.time.get_ticks()
    dt = current_tick - last_tick
    last_tick = current_tick

    # ----------------------------------
    # 5.1 イベント処理（キーボード入力など）
    # ----------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # 待機画面でスペースキーが押されたらゲーム開始/リトライ
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and game_state != "PLAYING":
                reset_game()

    # ----------------------------------
    # 5.2 ロジック更新（プレイ中の当たり判定・移動計算）
    # ----------------------------------
    if game_state == "PLAYING":
        # アナログ時計用のタイマー進行 (10000ms = 10秒で1周)
        old_timer = cycle_timer
        cycle_timer += dt
        
        # 5秒経過（6時の位置）で指示変更
        if old_timer < 5000 and cycle_timer >= 5000:
            current_inst = random.choice(instructions)
            play_sound(se_inst_change) 
        
        # 10秒経過（12時の位置に戻る）で手変更
        if cycle_timer >= 10000:
            cycle_timer -= 10000
            robot_hand = random.choice(hand_types)
            send_hand_to_m5(robot_hand)
            play_sound(se_hand_change) 

        # プレイヤーの移動とジャンプ処理
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
            if keys[pygame.K_DOWN]: velocity_y += 4 # 下キーで急降下
            player_y += velocity_y
            velocity_y += gravity
            # 着地判定
            if player_y >= HEIGHT - player_size - 20:
                player_y, is_jumping, velocity_y = HEIGHT - player_size - 20, False, 0

        # ボールの生成
        spawn_timer += dt
        if spawn_timer > 1000: # 1秒ごとに生成
            spawn_ball()
            spawn_timer = 0

        # ボールの落下と当たり判定
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
                balls.remove(ball) # 画面外に出たら消去

        # 勝敗チェック
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
        # 背景
        if img_bg: screen.blit(img_bg, (0, 0))
        else: screen.fill(WHITE)

        # UI: 体力とスコアゲージ
        screen.blit(font.render(f"HP: {'♥' * hp}", True, RED), (10, 10))
        pygame.draw.rect(screen, GRAY, (10, 45, 200, 20)) # 背景ゲージ
        fill_width = min(200, int((score / 100) * 200))
        pygame.draw.rect(screen, GREEN, (10, 45, fill_width, 20)) # 獲得ゲージ
        pygame.draw.rect(screen, BLACK, (10, 45, 200, 20), 2) # 枠線
        screen.blit(font.render("POINT", True, BLACK), (10, 70))

        # UI: アナログ時計（中央）
        clock_center = (WIDTH // 2, 70)
        clock_r = 45
        pygame.draw.circle(screen, LIGHT_RED, clock_center, clock_r, draw_top_right=True, draw_bottom_right=True)
        pygame.draw.circle(screen, LIGHT_BLUE, clock_center, clock_r, draw_top_left=True, draw_bottom_left=True)
        pygame.draw.circle(screen, BLACK, clock_center, clock_r, 2)
        
        screen.blit(font.render("手", True, BLUE), (clock_center[0] - 80, clock_center[1] - 15))
        screen.blit(font.render("指示", True, RED), (clock_center[0] + 55, clock_center[1] - 15))

        # 時計の針の描画 (0〜10000ms を 0〜360度に変換)
        angle = (cycle_timer / 10000.0) * 360
        rad = math.radians(angle)
        needle_x = clock_center[0] + clock_r * math.sin(rad)
        needle_y = clock_center[1] - clock_r * math.cos(rad)
        pygame.draw.line(screen, BLACK, clock_center, (needle_x, needle_y), 3)

        # 現在の指示テキスト
        inst_text = huge_font.render(current_inst, True, RED)
        screen.blit(inst_text, (WIDTH//2 - inst_text.get_width()//2, 130))

        # プレイヤーとボールの描画
        if img_player: screen.blit(img_player, (player_x, player_y))
        else: pygame.draw.rect(screen, BLACK, player_rect)

        for ball in balls:
            img = img_balls[ball["type"]]
            if img: screen.blit(img, (ball["rect"].x, ball["rect"].y))
            else: pygame.draw.ellipse(screen, ball["color"], ball["rect"])

    else:
        # タイトル・待機・リトライ画面
        screen.fill(WHITE)
        title_text = huge_font.render("じゃんけんゲーム", True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 100))
        
        # 直前の勝敗結果
        if game_state == "WIN":
            res_text = large_font.render("CLEAR!", True, GREEN)
            screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))
        elif game_state == "LOSE":
            res_text = large_font.render("GAME OVER", True, RED)
            screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))

        # 点滅テキスト（500ms間隔）
        blink_str = "Press SPACE to Play" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))

        # クレジット表記（右下）
        credit_text1 = font.render("背景素材: ゲームまてりあるず", True, GRAY)
        credit_text2 = font.render("https://game-materials.com/", True, GRAY)
        screen.blit(credit_text1, (WIDTH - credit_text1.get_width() - 10, HEIGHT - 70))
        screen.blit(credit_text2, (WIDTH - credit_text2.get_width() - 10, HEIGHT - 35))

    # 画面の更新とFPS設定
    pygame.display.flip()
    clock.tick(60)

# ゲーム終了時の処理
if ser is not None: ser.close()
pygame.quit()
sys.exit()