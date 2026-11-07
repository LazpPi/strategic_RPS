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
    """
    PCに接続されているUSBデバイスの中から、M5StickCと思われるポートを自動探索する関数。
    OSごとに一般的なポート名をフォールバックとして返す。
    """
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

# M5StickCとの通信確立を試みる
try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print(f"M5StickCと接続しました！ (ポート: {PORT})")
    # 接続直後に生存確認用（ハートビート）のダミー信号を送り、M5StickC側をCONNECTED状態にする
    ser.write(b'\n')
except Exception:
    ser = None
    print("M5StickCが見つかりません。ゲーム単体で起動します。")

def send_hand_to_m5(hand):
    """
    M5StickCに対してロボットハンドの形を指示する文字（P, G, C）を送信する関数。
    """
    if ser is None: return
    try:
        if hand == "グー": ser.write(b"G")
        elif hand == "チョキ": ser.write(b"C")
        elif hand == "パー": ser.write(b"P")
    except Exception as e:
        print(f"送信エラー: {e}")


# ==========================================
# 2. Pygame・画面・フォントの初期設定
# ==========================================
# 音声の遅延を防ぐためのミキサー初期化
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

# コントローラー（ジョイパッド）の接続設定
pygame.joystick.init()
joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"コントローラー接続: {joystick.get_name()}")
else:
    print("コントローラー未接続：キーボード操作で起動します")

def joy_button_pressed(button_number):
    """コントローラーの特定のボタンが押されているか判定する関数"""
    return (joystick is not None and joystick.get_init() and 
            button_number < joystick.get_numbuttons() and joystick.get_button(button_number))

# ウィンドウの設定
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED, display=1)
pygame.display.set_caption("戦略的じゃんけん MVP")
clock = pygame.time.Clock()

# 色の定義 (RGB)
WHITE, BLACK, GRAY = (255, 255, 255), (30, 30, 30), (200, 200, 200)
DARK_GRAY = (100, 100, 100) 
RED, GREEN, BLUE = (255, 100, 100), (100, 255, 100), (100, 100, 255)
ORANGE = (255, 150, 0)
YELLOW = (255, 220, 0)
LIGHT_RED, LIGHT_BLUE = (255, 200, 200), (200, 200, 255)
BROWN = (139, 69, 19) 

# 日本語フォントの読み込み（OSごとに存在するフォントを順番に探す）
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
        # フォントファイルが見つからない場合はPygameのデフォルトマッチングを使用
        font_name = pygame.font.match_font(['hiraginosans', 'meiryo', 'msgothic', 'notosanscjkjp'])
        font = pygame.font.Font(font_name, 24)
        large_font = pygame.font.Font(font_name, 40)
        mid_font = pygame.font.Font(font_name, 60)
        huge_font = pygame.font.Font(font_name, 80)
except:
    # 最終手段としてシステムデフォルトフォント
    font = large_font = mid_font = huge_font = pygame.font.Font(None, 40)


# ==========================================
# 3. 素材（画像・音声）の読み込み
# ==========================================
player_size, ball_size = 50, 60

def load_image(filename, size):
    """画像を読み込んで指定サイズにリサイズする関数"""
    filepath = os.path.join("images", filename)
    if os.path.exists(filepath):
        return pygame.transform.scale(pygame.image.load(filepath).convert_alpha(), size)
    return None

def load_sound(filename):
    """効果音を読み込む関数"""
    filepath = os.path.join("sounds", filename)
    if os.path.exists(filepath):
        return pygame.mixer.Sound(filepath)
    return None

def play_sound(sound):
    """サウンドオブジェクトが存在する場合のみ再生する関数"""
    if sound: sound.play()

# 画像リソースのロード
img_player = load_image("player.png", (player_size, player_size))
img_balls = {
    "グー": load_image("rock.png", (ball_size, ball_size)),
    "チョキ": load_image("scissors.png", (ball_size, ball_size)),
    "パー": load_image("paper.png", (ball_size, ball_size))
}
img_bg = load_image("bg.jpg", (WIDTH, HEIGHT))

# 音声リソースのロード
se_jump = load_sound("jump.mp3")
se_correct = load_sound("correct.mp3")
se_wrong = load_sound("wrong.mp3")
se_inst_change = load_sound("count.mp3") 
se_hand_change = load_sound("count.mp3") 
se_clear = load_sound("clear.mp3")

# BGMのパス定義（ロードと再生はシーンに合わせて行う）
bgm_path = os.path.join("sounds", "bgm.mp3")
ending_bgm_path = os.path.join("sounds", "ending.mp3") 


# ==========================================
# 4. ゲームルールの設定と変数
# ==========================================
player_speed = 7
jump_speed = 16
gravity = 1

# 足場の配置（[X座標, Y座標, 幅, 高さ]）
platforms = [
    pygame.Rect(100, 460, 150, 20),
    pygame.Rect(550, 460, 150, 20),
    pygame.Rect(325, 350, 150, 20)
]

hand_types = ["グー", "チョキ", "パー"]
ball_colors = {"グー": RED, "チョキ": GREEN, "パー": BLUE} # 画像がない場合の代替色
instructions = ["勝て", "負けろ", "あいこ"]

# ゲーム全体の進行状況を管理する変数
game_state = "HOME" # HOME, TUTORIAL, TUTORIAL_WARNING, PLAYING_DEMO, PLAYING, RESULT_RETRY, RESULT_END
play_count = 0      # 現在何ラウンド目か (1〜3)
clear_count = 0     # クリアした回数
last_result = ""    # 直前のラウンドの結果（CLEAR!, GAME OVER, TIME UP）

# 各ラウンドごとの動的変数（初期値）
play_time = 60.0
spawn_interval = 750
target_score = 5
tutorial_step = 0 
demo_timer = 0 
tutorial_warning_done = False 

def start_play():
    """
    新しいラウンドを開始するための初期化処理。
    現在の play_count に応じて難易度（HP、時間設定など）を切り替える。
    """
    global hp, score, game_state, balls, player_x, player_y, velocity_y, is_jumping
    global robot_hand, current_inst, cycle_timer, play_count, play_time
    global invincible_timer, spawn_interval, target_score, tutorial_step, demo_timer, tutorial_warning_done
    
    play_count += 1
    score = 0
    
    # ラウンドごとの難易度と状態設定
    if play_count == 1:
        play_time = 60.0
        spawn_interval = 750
        hp = 5
        target_score = 5
        game_state = "TUTORIAL" # 1ラウンド目はチュートリアルから開始
        tutorial_step = 0
        demo_timer = 0
        tutorial_warning_done = False 
    elif play_count == 2:
        play_time = 45.0
        spawn_interval = 750
        hp = 4
        target_score = 6 
        game_state = "PLAYING"
    else: # 3rd round以降
        play_time = 30.0
        spawn_interval = 500
        hp = 3
        target_score = 8 
        game_state = "PLAYING"

    # 変数のリセット
    balls = []
    invincible_timer = 0
    player_x, player_y = WIDTH // 2, HEIGHT - player_size - 20
    velocity_y, is_jumping = 0, False
    cycle_timer = 0
    
    # 最初の手と指示をランダムに決定してM5StickCに送信
    robot_hand = random.choice(hand_types)
    current_inst = random.choice(instructions)
    send_hand_to_m5(robot_hand)
    
    print(f"\n--- Round {play_count} スタート！ (制限時間: {play_time}秒 / HP: {hp} / 目標: {target_score}pt) ---")
    print(f"🤖 初期の手: 【 {robot_hand} 】 / 指示: 【 {current_inst} 】")
    
    # BGMの再生を開始
    if os.path.exists(bgm_path):
        pygame.mixer.music.load(bgm_path)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)

def spawn_ball():
    """上から降ってくるボール（手）を生成する関数"""
    b_type = random.choice(hand_types)
    x = random.randint(50, WIDTH - 50)
    balls.append({"rect": pygame.Rect(x, -50, ball_size, ball_size), "type": b_type, "color": ball_colors[b_type]})

def get_correct_hand(robot, inst):
    """
    現在の「ロボットの手」と「指示（勝て・負けろ・あいこ）」から、
    プレイヤーが拾うべき正解の手を判定する関数。
    """
    if inst == "あいこ": return robot
    elif inst == "勝て": return {"グー": "パー", "チョキ": "グー", "パー": "チョキ"}[robot]
    elif inst == "負けろ": return {"グー": "チョキ", "チョキ": "パー", "パー": "グー"}[robot]


# ==========================================
# 5. メインループ
# ==========================================
last_tick = pygame.time.get_ticks()
spawn_timer = 0
pc_heartbeat_timer = 0 
running = True
round_names = ["1st", "2nd", "3rd"]

while running:
    # デルタタイム（前フレームからの経過時間）の計算
    current_tick = pygame.time.get_ticks()
    dt = current_tick - last_tick
    last_tick = current_tick

    # 1秒ごとにM5StickCへ生存確認（ハートビート）を送信し、通信断を検知させる
    pc_heartbeat_timer += dt
    if pc_heartbeat_timer >= 1000:
        if ser is not None:
            try:
                ser.write(b'\n')
            except Exception as e:
                pass
        pc_heartbeat_timer = 0

    # ----------------------------------
    # 5.1 イベント処理 (入力判定)
    # ----------------------------------
    action_pressed = False 
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_SPACE:
                action_pressed = True
                
            # --- テスト運用用ショートカットキー（強制クリア / 強制ゲームオーバー） ---
            if event.key == pygame.K_w and game_state in ("PLAYING", "PLAYING_DEMO"):
                score = target_score
            if event.key == pygame.K_l and game_state in ("PLAYING", "PLAYING_DEMO"):
                hp = 0

        # コントローラーの主要ボタン(A, B, X, Yなど)が押された場合
        if event.type == pygame.JOYBUTTONDOWN and event.button in (0, 1, 2, 3, 4):
            action_pressed = True

    # ゲームプレイ中以外でAボタンが押された場合の画面遷移ロジック
    if action_pressed and game_state not in ("PLAYING", "PLAYING_DEMO"):
        if game_state == "HOME":
            play_count = 0
            clear_count = 0
            start_play()
        elif game_state == "TUTORIAL":
            # チュートリアルの進行
            if tutorial_step == 0:
                tutorial_step = 1 
            elif tutorial_step == 1:
                tutorial_step = 2
                game_state = "PLAYING_DEMO" 
                demo_timer = 0
            elif tutorial_step == 3:
                game_state = "PLAYING" 
        elif game_state == "TUTORIAL_WARNING":
            game_state = "PLAYING" # 警告表示を解除してゲームを再開
        elif game_state == "RESULT_RETRY":
            start_play()
        elif game_state == "RESULT_END":
            pygame.mixer.music.stop()
            game_state = "HOME" 

    # ----------------------------------
    # 5.2 ロジック更新 (ゲーム進行)
    # ----------------------------------
    if game_state in ("PLAYING", "PLAYING_DEMO"):
        
        # 制限時間の減少
        play_time -= dt / 1000.0
        if play_time <= 0:
            play_time = 0
            
        # デモ状態の進行（1.5秒経過で次のチュートリアルステップへ強制遷移）
        if game_state == "PLAYING_DEMO":
            demo_timer += dt
            if demo_timer >= 1500: 
                game_state = "TUTORIAL"
                tutorial_step = 3

        # 無敵時間（点滅時間）の減少
        if invincible_timer > 0:
            invincible_timer -= dt

        old_timer = cycle_timer
        cycle_timer += dt
        
        # 1st roundで9秒経過した瞬間に一時停止して警告を出す
        if play_count == 1 and not tutorial_warning_done and cycle_timer >= 9000:
            tutorial_warning_done = True
            game_state = "TUTORIAL_WARNING"
        
        # 手と指示の切り替えロジック（ラウンドごとに周期とズレが異なる）
        if play_count == 1:
            # 1st: 10秒周期で手と指示が同時に切り替わる
            if cycle_timer >= 10000:
                cycle_timer -= 10000
                robot_hand = random.choice(hand_types)
                current_inst = random.choice(instructions)
                send_hand_to_m5(robot_hand)
                play_sound(se_hand_change) 
                print(f"🤖 手と指示が変更されました: 手【{robot_hand}】 指示【{current_inst}】")
        elif play_count == 2:
            # 2nd: 9秒周期で手、4.5秒周期で指示が切り替わる
            if old_timer < 4500 and cycle_timer >= 4500:
                current_inst = random.choice(instructions)
                play_sound(se_inst_change) 
            if cycle_timer >= 9000:
                cycle_timer -= 9000
                robot_hand = random.choice(hand_types)
                send_hand_to_m5(robot_hand)
                play_sound(se_hand_change) 
                print(f"🤖 手が変更されました: 【 {robot_hand} 】")
        else:
            # 3rd: 6秒周期で手、3秒周期で指示が切り替わる（スピードアップ）
            if old_timer < 3000 and cycle_timer >= 3000:
                current_inst = random.choice(instructions)
                play_sound(se_inst_change) 
            if cycle_timer >= 6000:
                cycle_timer -= 6000
                robot_hand = random.choice(hand_types)
                send_hand_to_m5(robot_hand)
                play_sound(se_hand_change) 
                print(f"🤖 手が変更されました: 【 {robot_hand} 】")

        # プレイヤーの移動入力処理
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

        # プレイヤーのジャンプ入力処理
        jump_pressed = (keys[pygame.K_UP] or joy_button_pressed(11) or 
                        axis_y <= -0.5 or axis_4 >= 0.8 or axis_5 >= 0.8)
        
        if jump_pressed and not is_jumping:
            is_jumping = True
            velocity_y = -jump_speed
            play_sound(se_jump)

        down_pressed = keys[pygame.K_DOWN] or joy_button_pressed(12)

        # 物理演算（ジャンプと重力、足場との当たり判定）
        if is_jumping:
            if down_pressed: velocity_y += 4 # 急降下
            player_y += velocity_y
            velocity_y += gravity
            
            # 地面との当たり判定
            if player_y >= HEIGHT - player_size - 20:
                player_y = HEIGHT - player_size - 20
                is_jumping = False
                velocity_y = 0
            else:
                # 足場との当たり判定（落下中のみ乗れる）
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
            # 足場から降りた場合の落下処理
            if player_y < HEIGHT - player_size - 20:
                player_rect = pygame.Rect(player_x, player_y + 1, player_size, player_size)
                on_plat = False
                for plat in platforms:
                    if player_rect.colliderect(plat):
                        on_plat = True
                        break
                if not on_plat:
                    is_jumping = True 

        # ボールの生成
        spawn_timer += dt
        if spawn_timer > spawn_interval:
            spawn_ball()
            spawn_timer = 0

        # ボールとプレイヤーの衝突判定
        player_rect = pygame.Rect(player_x, player_y, player_size, player_size)
        correct_hand = get_correct_hand(robot_hand, current_inst)

        for ball in balls[:]:
            ball["rect"].y += 5
            if player_rect.colliderect(ball["rect"]):
                if ball["type"] == correct_hand:
                    score += 1 
                    play_sound(se_correct)
                    balls.remove(ball)
                else:
                    hp -= 1
                    play_sound(se_wrong)
                    invincible_timer = 1000 # 被弾時は1秒間点滅する
                    balls.remove(ball)
            # 画面外に出たボールを消去
            elif ball["rect"].y > HEIGHT:
                balls.remove(ball)

        # ラウンド終了判定
        if game_state in ("PLAYING", "PLAYING_DEMO"):
            if hp <= 0 or score >= target_score or play_time <= 0:
                if score >= target_score:
                    last_result = "CLEAR!"
                    clear_count += 1
                    play_sound(se_clear)
                elif hp <= 0:
                    last_result = "GAME OVER"
                else:
                    last_result = "TIME UP"
                    
                pygame.mixer.music.stop()
                
                print(f"--- Round {play_count} 結果: {last_result} ---")
                
                # 全3ラウンド終了時の処理
                if play_count >= 3:
                    game_state = "RESULT_END" 
                    
                    # ターミナルへ最終結果（クリア回数とチケット枚数）を出力する
                    ticket_count = 1 if clear_count <= 1 else clear_count
                    print("==================================================")
                    print(f"      3セット終了！ (勝ち数: {clear_count}/3)")
                    print(f"      チケット配布枚数: {ticket_count}枚")
                    print("==================================================")
                    
                    # M5StickCへ最終クリア回数(0〜3)を送信して画面を更新させる
                    if ser is not None:
                        try:
                            ser.write(str(clear_count).encode())
                        except Exception as e:
                            pass
                            
                    # エンディングBGMの再生
                    if os.path.exists(ending_bgm_path):
                        pygame.mixer.music.load(ending_bgm_path)
                        pygame.mixer.music.set_volume(0.5)
                        pygame.mixer.music.play(-1)
                else:
                    game_state = "RESULT_RETRY" 
    
    # ----------------------------------
    # 5.3 画面の描画
    # ----------------------------------
    # ゲームプレイ画面（チュートリアル等含む）の描画
    if game_state in ("PLAYING", "PLAYING_DEMO", "TUTORIAL", "TUTORIAL_WARNING"):
        
        # 背景
        if img_bg: screen.blit(img_bg, (0, 0))
        else: screen.fill(WHITE)
        
        # 足場
        for plat in platforms:
            pygame.draw.rect(screen, BROWN, plat)
            pygame.draw.rect(screen, BLACK, plat, 2) 

        # HPゲージの描画
        screen.blit(font.render(f"{'♥' * hp}", True, RED), (10, 10))
        
        # ポイントゲージの描画
        pygame.draw.rect(screen, GRAY, (10, 45, 200, 20))
        fill_width = min(200, int((score / target_score) * 200))
        pygame.draw.rect(screen, ORANGE, (10, 45, fill_width, 20)) 
        pygame.draw.rect(screen, BLACK, (10, 45, 200, 20), 2)
        
        # ポイントゲージの目盛り
        for i in range(1, target_score):
            line_x = 10 + i * (200 // target_score)
            pygame.draw.line(screen, BLACK, (line_x, 45), (line_x, 65), 1)

        screen.blit(font.render("POINT", True, BLACK), (10, 70))

        # 残り時間の描画（残り10秒を切ったら心臓の鼓動のように拡大縮小する演出）
        time_str = str(math.ceil(play_time))
        scale = 1.0
        if play_time <= 10 and game_state in ("PLAYING", "PLAYING_DEMO"):
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
        # 統合UIパネルの描画（指示や手を視覚的に表示する領域）
        # ==========================================
        ui_w, ui_h = 220, 155
        ui_x = WIDTH // 2 - ui_w // 2
        ui_y = 20
        
        ui_rect = pygame.Rect(ui_x, ui_y, ui_w, ui_h)
        pygame.draw.rect(screen, DARK_GRAY, ui_rect, border_top_left_radius=60, border_top_right_radius=60)
        pygame.draw.rect(screen, BLACK, ui_rect, 3, border_top_left_radius=60, border_top_right_radius=60)
        
        line_y = ui_y + 90
        pygame.draw.line(screen, BLACK, (ui_x, line_y), (ui_x + ui_w, line_y), 3)

        clock_r = 40
        inst_center = (WIDTH // 2 - 45, ui_y + 45)
        hand_center = (WIDTH // 2 + 45, ui_y + 45)
        
        # --- 左側：指示切り替えタイマー ---
        pygame.draw.circle(screen, LIGHT_RED, inst_center, clock_r)
        pygame.draw.circle(screen, BLACK, inst_center, clock_r, 2)
        pygame.draw.line(screen, BLACK, (inst_center[0], inst_center[1] - clock_r), (inst_center[0], inst_center[1] - clock_r + 8), 3)
        
        inst_lbl = font.render("指示", True, (255, 130, 130))
        screen.blit(inst_lbl, (inst_center[0] - inst_lbl.get_width()//2, inst_center[1] - inst_lbl.get_height()//2))
        
        # ラウンドに応じた針の回転角度計算
        if play_count == 1:
            inst_angle = (cycle_timer / 10000.0) * 360
        elif play_count == 2:
            inst_angle = ((cycle_timer % 4500) / 4500.0) * 360
        else: 
            inst_angle = ((cycle_timer % 3000) / 3000.0) * 360
            
        rad_inst = math.radians(inst_angle)
        pygame.draw.line(screen, BLACK, inst_center, 
                         (inst_center[0] + clock_r * math.sin(rad_inst), inst_center[1] - clock_r * math.cos(rad_inst)), 3)

        # --- 右側：ロボットの手切り替えタイマー ---
        pygame.draw.circle(screen, LIGHT_BLUE, hand_center, clock_r)
        pygame.draw.circle(screen, BLACK, hand_center, clock_r, 2)
        pygame.draw.line(screen, BLACK, (hand_center[0], hand_center[1] - clock_r), (hand_center[0], hand_center[1] - clock_r + 8), 3)
        
        hand_lbl = font.render("手", True, (130, 130, 255))
        screen.blit(hand_lbl, (hand_center[0] - hand_lbl.get_width()//2, hand_center[1] - hand_lbl.get_height()//2))
        
        # ラウンドに応じた針の回転角度計算
        if play_count == 1:
            hand_angle = (cycle_timer / 10000.0) * 360
        elif play_count == 2:
            hand_angle = (cycle_timer / 9000.0) * 360
        else:
            hand_angle = (cycle_timer / 6000.0) * 360
            
        rad_hand = math.radians(hand_angle)
        pygame.draw.line(screen, BLACK, hand_center, 
                         (hand_center[0] + clock_r * math.sin(rad_hand), hand_center[1] - clock_r * math.cos(rad_hand)), 3)

        # --- 中央下：現在の指示テキスト ---
        inst_text = mid_font.render(current_inst, True, RED)
        inst_rect = inst_text.get_rect(center=(WIDTH//2, line_y + (ui_h - 90)//2))
        screen.blit(inst_text, inst_rect)

        # プレイヤーの描画（ダメージを受けた場合は一定時間点滅させる）
        if invincible_timer <= 0 or (invincible_timer // 100) % 2 == 0:
            if img_player: screen.blit(img_player, (player_x, player_y))
            else: pygame.draw.rect(screen, BLACK, player_rect)

        # 降ってくるボール（手）の描画
        for ball in balls:
            img = img_balls[ball["type"]]
            if img: screen.blit(img, (ball["rect"].x, ball["rect"].y))
            else: pygame.draw.ellipse(screen, ball["color"], ball["rect"])
            
        # ==========================================
        # チュートリアル・警告時のオーバーレイ演出
        # ==========================================
        if game_state in ("TUTORIAL", "TUTORIAL_WARNING"):
            # 画面全体を半透明の黒で覆う
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(150)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))
            
            # テキストをチカチカ点滅させる演出フラグ
            blink = (pygame.time.get_ticks() // 500) % 2 == 0
            
            if blink:
                if game_state == "TUTORIAL":
                    if tutorial_step == 0:
                        msg1 = "ロボットの手を見て！"
                    elif tutorial_step == 1:
                        msg1 = "指示を見て！"
                        
                        # 中央の指示テキストを下から指し示す黄色の矢印
                        arrow_tip_x = WIDTH // 2
                        arrow_tip_y = 175
                        p1 = (arrow_tip_x, arrow_tip_y)       
                        p2 = (arrow_tip_x - 20, arrow_tip_y + 30) 
                        p3 = (arrow_tip_x + 20, arrow_tip_y + 30) 
                        pygame.draw.polygon(screen, YELLOW, [p1, p2, p3])
                        
                    else: 
                        msg1 = "正しい手を拾え！"
                        
                    txt1 = mid_font.render(msg1, True, YELLOW)
                    
                    # チュートリアル中は「を」が中央に来るようにテキスト位置を微調整する
                    if tutorial_step == 1:
                        offset = mid_font.render("指示", True, YELLOW).get_width() + (mid_font.render("を", True, YELLOW).get_width() // 2)
                        screen.blit(txt1, (WIDTH//2 - offset, HEIGHT//2 - 60))
                    else:
                        screen.blit(txt1, (WIDTH//2 - txt1.get_width()//2, HEIGHT//2 - 60))
                        
                elif game_state == "TUTORIAL_WARNING":
                    msg1 = "指示＆手が変わるぞ"
                    txt1 = mid_font.render(msg1, True, YELLOW)
                    
                    # 左右のタイマーをそれぞれ指し示す黄色い矢印
                    tip_x1 = WIDTH // 2 - 45
                    tip_y = 115
                    pygame.draw.polygon(screen, YELLOW, [(tip_x1, tip_y), (tip_x1 - 15, tip_y + 25), (tip_x1 + 15, tip_y + 25)])
                    
                    tip_x2 = WIDTH // 2 + 45
                    pygame.draw.polygon(screen, YELLOW, [(tip_x2, tip_y), (tip_x2 - 15, tip_y + 25), (tip_x2 + 15, tip_y + 25)])
                    
                    screen.blit(txt1, (WIDTH//2 - txt1.get_width()//2, HEIGHT//2 - 60))


    # === ホーム画面の描画 ===
    elif game_state == "HOME":
        screen.fill(WHITE)
        title_text = huge_font.render("じゃんけんゲーム", True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 100))
        
        ctrl_text = large_font.render("十字キーで操作", True, RED)
        screen.blit(ctrl_text, (WIDTH//2 - ctrl_text.get_width()//2, HEIGHT//2 + 10))
            
        blink_str = "Aボタンでスタート" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))
            
        credit_text1 = font.render("背景素材: ゲームまてりあるず", True, GRAY)
        credit_text2 = font.render("https://game-materials.com/", True, GRAY)
        screen.blit(credit_text1, (WIDTH - credit_text1.get_width() - 10, HEIGHT - 70))
        screen.blit(credit_text2, (WIDTH - credit_text2.get_width() - 10, HEIGHT - 35))

    # === リトライ画面の描画 ===
    elif game_state == "RESULT_RETRY":
        screen.fill(WHITE)
        round_str = f"{round_names[play_count]} round"
        title_text = huge_font.render(round_str, True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 100))
        
        res_color = GREEN if last_result == "CLEAR!" else RED
        res_text = large_font.render(last_result, True, res_color)
        screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))

        blink_str = "Aボタンでスタート" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))

    # === 最終結果画面の描画 ===
    elif game_state == "RESULT_END":
        screen.fill(WHITE)
        
        # クリア回数に応じたメッセージの分岐設定
        if clear_count <= 1:
            msg1 = "惜しい！"
            msg2 = "スタッフからチケット1枚受け取ってね！"
        elif clear_count == 2:
            msg1 = "2回クリア！おめでとう！"
            msg2 = "スタッフからチケット2枚受け取ってね！"
        else: # clear_count == 3
            msg1 = "3回クリア！パーフェクト！"
            msg2 = "スタッフからチケット3枚受け取ってね！"
            
        # 第一メッセージは赤色で強調表示する
        end_text1 = mid_font.render(msg1, True, RED)
        end_text2 = large_font.render(msg2, True, BLACK)
        
        screen.blit(end_text1, (WIDTH//2 - end_text1.get_width()//2, HEIGHT//2 - 90))
        screen.blit(end_text2, (WIDTH//2 - end_text2.get_width()//2, HEIGHT//2 - 10))
        
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