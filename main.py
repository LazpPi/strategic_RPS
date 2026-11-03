import pygame
import random
import sys
import os
import math
import serial
import serial.tools.list_ports # 接続されているUSBポートを自動で探すためのライブラリ
import platform                # 実行中のOS（Mac/Windows/Linux）を判別するライブラリ

# ==========================================
# 1. M5StickCとのシリアル通信設定（OS自動判別）
# ==========================================
def find_m5stick_port():
    """OSを問わず、接続されているUSBシリアルポートを自動検索する関数"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # ポートの説明文や名前に「USB」が含まれていれば、M5StickCが繋がっているとみなす
        if "USB" in port.description.upper() or "USB" in port.device.upper():
            return port.device
    
    # 自動検出で見つからなかった場合は、OSごとの定番の名前をとりあえず返す（保険）
    sys_name = platform.system()
    if sys_name == "Windows": return "COM3"
    elif sys_name == "Darwin": return "/dev/cu.usbserial-51526A2D93" # Mac
    else: return "/dev/ttyUSB0" # Raspberry PiなどのLinux系

PORT = find_m5stick_port()
BAUD_RATE = 115200 # M5StickC側の設定と合わせる通信速度

# M5StickCとの接続を試みる
try:
    # timeoutを設定することで、通信が詰まってゲームがフリーズするのを防ぐ
    ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    print(f"M5StickCと接続しました！ (ポート: {PORT})")
except Exception:
    ser = None # 接続失敗時はNoneにしておき、エラーでゲームが落ちないようにする
    print("M5StickCが見つかりません。ゲーム単体で起動します。")

def send_hand_to_m5(hand):
    """M5StickCへ手の形を1文字（G/C/P）で送信する関数"""
    if ser is None: return # 未接続なら何もしない
    if hand == "グー": ser.write(b"G")
    elif hand == "チョキ": ser.write(b"C")
    elif hand == "パー": ser.write(b"P")


# ==========================================
# 2. Pygame・画面・フォントの初期設定（全OS対応）
# ==========================================
# 音が遅れて鳴る（音ズレ）現象を防ぐための事前設定
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

# ==========================================
# コントローラー設定（未接続でもキーボードで起動可能）
# ==========================================
pygame.joystick.init()
joystick = None

if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"コントローラー接続: {joystick.get_name()}")
    print(f"ボタン数: {joystick.get_numbuttons()} / Axis数: {joystick.get_numaxes()}")
else:
    print("コントローラー未接続：キーボード操作で起動します")

def joy_button_pressed(button_number):
    """指定番号のコントローラーボタンが押されているか確認"""
    return (
        joystick is not None
        and joystick.get_init()
        and button_number < joystick.get_numbuttons()
        and joystick.get_button(button_number)
    )


WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("戦略的じゃんけん MVP")
clock = pygame.time.Clock() # フレームレート（FPS）管理用

# よく使う色の定義 (R, G, B)
WHITE, BLACK, GRAY = (255, 255, 255), (30, 30, 30), (200, 200, 200)
RED, GREEN, BLUE = (255, 100, 100), (100, 255, 100), (100, 100, 255)
LIGHT_RED, LIGHT_BLUE = (255, 200, 200), (200, 200, 255) # 時計の盤面用の薄い色

# Mac / Windows / Raspberry Pi の各標準日本語フォント候補リスト
font_paths = [
    "/System/Library/Fonts/Hiragino Sans W4.ttc", # Mac用
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc", # Mac用（古いOS）
    "C:\\Windows\\Fonts\\meiryo.ttc", # Windows用（メイリオ）
    "C:\\Windows\\Fonts\\msgothic.ttc", # Windows用（MSゴシック）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", # Raspberry Pi用
    "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf" # Linux汎用
]
# リストの中から、実際にそのパソコンの中に存在する最初のフォントを探す
jp_font_path = next((p for p in font_paths if os.path.exists(p)), None)

try:
    if jp_font_path:
        # 見つかったフォントファイルを直接読み込む
        font = pygame.font.Font(jp_font_path, 24)
        large_font = pygame.font.Font(jp_font_path, 40)
        huge_font = pygame.font.Font(jp_font_path, 80)
    else:
        # 見つからない場合はPygameの自動検索機能に任せる
        font_name = pygame.font.match_font(['hiraginosans', 'meiryo', 'msgothic', 'notosanscjkjp'])
        font = pygame.font.Font(font_name, 24)
        large_font = pygame.font.Font(font_name, 40)
        huge_font = pygame.font.Font(font_name, 80)
except:
    # 最悪、日本語フォントが全く見つからなかった場合の最後の手段（英語フォント）
    font = large_font = huge_font = pygame.font.Font(None, 40)


# ==========================================
# 3. 素材（画像・音声）の読み込み
# ==========================================
player_size, ball_size = 50, 60

def load_image(filename, size):
    """imagesフォルダから画像を読み込み、指定サイズにリサイズする"""
    # os.path.joinを使うと、Mac(/)でもWindows(\)でも正しいパス記号で繋いでくれる
    filepath = os.path.join("images", filename)
    if os.path.exists(filepath):
        # convert_alpha()を付けると、背景が透明な画像（PNGなど）が綺麗に処理される
        return pygame.transform.scale(pygame.image.load(filepath).convert_alpha(), size)
    return None

def load_sound(filename):
    """soundsフォルダから効果音を読み込む"""
    filepath = os.path.join("sounds", filename)
    if os.path.exists(filepath):
        return pygame.mixer.Sound(filepath)
    return None

def play_sound(sound):
    """音声ファイルが正しく読み込まれていれば再生する安全な関数"""
    if sound: sound.play()

# 画像ファイルの読み込み
img_player = load_image("player.png", (player_size, player_size))
img_balls = {
    "グー": load_image("rock.png", (ball_size, ball_size)),
    "チョキ": load_image("scissors.png", (ball_size, ball_size)),
    "パー": load_image("paper.png", (ball_size, ball_size))
}
img_bg = load_image("bg.jpg", (WIDTH, HEIGHT))

# 効果音ファイルの読み込み
se_jump = load_sound("jump.mp3")
se_correct = load_sound("correct.mp3")
se_wrong = load_sound("wrong.mp3")
se_inst_change = load_sound("count.mp3") 
se_hand_change = load_sound("count.mp3") 
se_clear = load_sound("clear.mp3")

# BGMの設定（ループ再生用）
bgm_path = os.path.join("sounds", "bgm.mp3")
if os.path.exists(bgm_path):
    pygame.mixer.music.load(bgm_path)
    pygame.mixer.music.set_volume(0.5) # 音量を50%にする


# ==========================================
# 4. ゲームルールの設定と関数
# ==========================================
player_speed = 7      # 左右の移動速度
jump_speed = 16       # ジャンプの初速（大きいほど高く飛ぶ）
gravity = 1           # 重力（毎フレーム下に向かって加速する量）

hand_types = ["グー", "チョキ", "パー"]
ball_colors = {"グー": RED, "チョキ": GREEN, "パー": BLUE} # 画像がない時の代替色
instructions = ["勝て", "負けろ", "あいこ"]

game_state = "TITLE" # 現在の画面状態（TITLE, PLAYING, WIN, LOSE）

def reset_game():
    """ゲーム開始時やリトライ時に、すべてのパラメータを初期状態に戻す"""
    # global宣言：関数外で定義された変数を上書きするために必要
    global hp, score, game_state, balls, player_x, player_y, velocity_y, is_jumping
    global robot_hand, current_inst, cycle_timer
    
    hp, score = 3, 0
    game_state = "PLAYING"
    balls = [] # 画面上のボールをすべて消す
    
    # プレイヤーを画面中央の下に配置
    player_x, player_y = WIDTH // 2, HEIGHT - player_size - 20
    velocity_y, is_jumping = 0, False
    
    cycle_timer = 0 # 時計のカウントダウンを0に戻す
    
    # 最初の手と指示をランダムに決定し、ロボットへ送信
    robot_hand = random.choice(hand_types)
    current_inst = random.choice(instructions)
    send_hand_to_m5(robot_hand)
    print(f"ゲーム開始: 最初の手を「{robot_hand}」にセットして送信しました！")
    
    # BGMのループ再生開始（-1で無限ループ）
    if os.path.exists(bgm_path):
        pygame.mixer.music.play(-1)

def spawn_ball():
    """画面上部からランダムなボールを1つ降らせる"""
    b_type = random.choice(hand_types)
    x = random.randint(50, WIDTH - 50) # 画面の端すぎない位置にランダム生成
    balls.append({"rect": pygame.Rect(x, -50, ball_size, ball_size), "type": b_type, "color": ball_colors[b_type]})

def get_correct_hand(robot, inst):
    """ロボットの現在の「手」と「指示」から、キャッチすべき正解の手を判定する"""
    if inst == "あいこ": return robot
    elif inst == "勝て": return {"グー": "パー", "チョキ": "グー", "パー": "チョキ"}[robot]
    elif inst == "負けろ": return {"グー": "チョキ", "チョキ": "パー", "パー": "グー"}[robot]


# ==========================================
# 5. メインループ（ゲームが起動している間ずっと回る処理）
# ==========================================
last_tick = pygame.time.get_ticks()
spawn_timer = 0
running = True

while running:
    # 経過時間（dt）の計算
    # パソコンの性能差による処理速度の違いを吸収し、タイマーを正確に進めるため
    current_tick = pygame.time.get_ticks()
    dt = current_tick - last_tick
    last_tick = current_tick

    # ----------------------------------
    # 5.1 イベント処理（キーボードやウィンドウの操作）
    # ----------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT: # ウィンドウの×ボタンが押されたら
            running = False
        if event.type == pygame.KEYDOWN:
            # 待機・結果画面：SPACEキーで開始・リトライ
            if event.key == pygame.K_SPACE and game_state != "PLAYING":
                reset_game()

        # コントローラーのButton 0～4：開始・リトライ
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button in (0, 1, 2, 3, 4) and game_state != "PLAYING":
                reset_game()

    # ----------------------------------
    # 5.2 ロジック更新（プレイ中の当たり判定・移動計算など）
    # ----------------------------------
    if game_state == "PLAYING":
        # 時計用タイマーの進行 (10000ms = 10秒で1周する時計)
        old_timer = cycle_timer
        cycle_timer += dt
        
        # 5秒経過（針が6時の位置に到達）した瞬間、指示だけを変更
        if old_timer < 5000 and cycle_timer >= 5000:
            current_inst = random.choice(instructions)
            play_sound(se_inst_change) 
        
        # 10秒経過（針が12時の位置に戻る）した瞬間、タイマーをリセットし手を手を変更
        if cycle_timer >= 10000:
            cycle_timer -= 10000
            robot_hand = random.choice(hand_types)
            send_hand_to_m5(robot_hand)
            play_sound(se_hand_change) 

        # プレイヤーの移動（キーボード＋コントローラー）
        keys = pygame.key.get_pressed()

        # コントローラーAxis取得
        axis_x = 0.0
        axis_y = 0.0
        axis_4 = -1.0
        axis_5 = -1.0

        if joystick is not None and joystick.get_init():
            if joystick.get_numaxes() > 0:
                axis_x = joystick.get_axis(0)
            if joystick.get_numaxes() > 1:
                axis_y = joystick.get_axis(1)
            if joystick.get_numaxes() > 4:
                axis_4 = joystick.get_axis(4)
            if joystick.get_numaxes() > 5:
                axis_5 = joystick.get_axis(5)

        # 左右移動：キーボード、ボタン13/14、Axis 0
        move_left = keys[pygame.K_LEFT] or joy_button_pressed(13) or axis_x <= -0.8
        move_right = keys[pygame.K_RIGHT] or joy_button_pressed(14) or axis_x >= 0.8

        if move_left and player_x > 0:
            player_x -= player_speed
        if move_right and player_x < WIDTH - player_size:
            player_x += player_speed

        # ジャンプ：上キー、Button 11、Axis 1のマイナス、
        # Axis 4またはAxis 5が1.0付近
        jump_pressed = (
            keys[pygame.K_UP]
            or joy_button_pressed(11)
            or axis_y <= -0.5
            or axis_4 >= 0.8
            or axis_5 >= 0.8
        )

        if jump_pressed and not is_jumping:
            is_jumping = True
            velocity_y = -jump_speed
            play_sound(se_jump)

        # 急降下：下キーまたはButton 12
        down_pressed = keys[pygame.K_DOWN] or joy_button_pressed(12)

        # ジャンプ中の重力と移動の処理
        if is_jumping:
            if down_pressed:
                velocity_y += 4 # 下キーを押すと急降下
            player_y += velocity_y
            velocity_y += gravity # 毎フレーム重力を足して落下させる
            
            # 着地判定（地面の高さに達したらジャンプ終了）
            if player_y >= HEIGHT - player_size - 20:
                player_y, is_jumping, velocity_y = HEIGHT - player_size - 20, False, 0

        # ボールの生成（1000ms = 1秒ごとに生成）
        spawn_timer += dt
        if spawn_timer > 1000:
            spawn_ball()
            spawn_timer = 0

        # ボールの落下と当たり判定の計算
        player_rect = pygame.Rect(player_x, player_y, player_size, player_size)
        correct_hand = get_correct_hand(robot_hand, current_inst)

        # ballsのリストをループ処理（[:]を使うことで、処理中のリスト要素削除バグを防ぐ）
        for ball in balls[:]:
            ball["rect"].y += 5 # ボールを下に落とす
            
            # プレイヤーとボールがぶつかったら（colliderect = 四角形同士の衝突判定）
            if player_rect.colliderect(ball["rect"]):
                if ball["type"] == correct_hand:
                    score += 10 # 正解ならポイント追加
                    play_sound(se_correct)
                else:
                    hp -= 1     # 不正解ならダメージ
                    play_sound(se_wrong)
                balls.remove(ball) # 当たったボールは消す
            
            # 画面外（下）まで落ちたボールも消す
            elif ball["rect"].y > HEIGHT:
                balls.remove(ball)

        # 勝敗チェック
        if hp <= 0: 
            game_state = "LOSE"
            pygame.mixer.music.stop() # 負けたらBGMを止める
        elif score >= 100: 
            game_state = "WIN"
            pygame.mixer.music.stop() # 勝ってもBGMを止める
            play_sound(se_clear)
    
    # ----------------------------------
    # 5.3 画面の描画（計算した結果を実際にモニターに映す処理）
    # ----------------------------------
    if game_state == "PLAYING":
        # 背景の描画
        if img_bg: screen.blit(img_bg, (0, 0)) # 画像があればそれを描く
        else: screen.fill(WHITE)               # なければ白く塗りつぶす

        # UI: 体力とスコアゲージの描画
        screen.blit(font.render(f"HP: {'♥' * hp}", True, RED), (10, 10))
        pygame.draw.rect(screen, GRAY, (10, 45, 200, 20)) # ゲージの灰色の下地
        fill_width = min(200, int((score / 100) * 200))   # スコアに応じた緑ゲージの幅を計算
        pygame.draw.rect(screen, GREEN, (10, 45, fill_width, 20)) # 緑ゲージ本体
        pygame.draw.rect(screen, BLACK, (10, 45, 200, 20), 2) # ゲージの黒い外枠
        screen.blit(font.render("POINT", True, BLACK), (10, 70))

        # UI: アナログ時計（中央）の描画
        clock_center = (WIDTH // 2, 70)
        clock_r = 45 # 時計の半径
        
        # 右半分（指示・赤系）と左半分（手・青系）の円を塗る
        pygame.draw.circle(screen, LIGHT_RED, clock_center, clock_r, draw_top_right=True, draw_bottom_right=True)
        pygame.draw.circle(screen, LIGHT_BLUE, clock_center, clock_r, draw_top_left=True, draw_bottom_left=True)
        pygame.draw.circle(screen, BLACK, clock_center, clock_r, 2) # 黒い外枠
        
        # 時計の横のラベル文字
        screen.blit(font.render("手", True, BLUE), (clock_center[0] - 80, clock_center[1] - 15))
        screen.blit(font.render("指示", True, RED), (clock_center[0] + 55, clock_center[1] - 15))

        # 時計の針の角度を計算して描画
        # cycle_timer(0〜10000) を割合にし、360を掛けて角度（angle）にする
        angle = (cycle_timer / 10000.0) * 360
        rad = math.radians(angle) # Pythonの三角関数はラジアンを使うため変換
        
        # サイン・コサインを使って、針の先端のX,Y座標を求める
        needle_x = clock_center[0] + clock_r * math.sin(rad)
        needle_y = clock_center[1] - clock_r * math.cos(rad)
        pygame.draw.line(screen, BLACK, clock_center, (needle_x, needle_y), 3) # 針を引く

        # 現在の指示テキスト（画面中央）
        inst_text = huge_font.render(current_inst, True, RED)
        screen.blit(inst_text, (WIDTH//2 - inst_text.get_width()//2, 130))

        # プレイヤーとボールの描画
        if img_player: screen.blit(img_player, (player_x, player_y))
        else: pygame.draw.rect(screen, BLACK, player_rect) # 画像がなければ黒い四角

        for ball in balls:
            img = img_balls[ball["type"]]
            if img: screen.blit(img, (ball["rect"].x, ball["rect"].y))
            else: pygame.draw.ellipse(screen, ball["color"], ball["rect"]) # 画像がなければ色付きの丸

    else:
        # ----------------------------------
        # タイトル・待機・リトライ画面の描画
        # ----------------------------------
        screen.fill(WHITE)
        title_text = huge_font.render("じゃんけんゲーム", True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 100))
        
        # 直前の勝敗結果があれば表示する
        if game_state == "WIN":
            res_text = large_font.render("CLEAR!", True, GREEN)
            screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))
        elif game_state == "LOSE":
            res_text = large_font.render("GAME OVER", True, RED)
            screen.blit(res_text, (WIDTH//2 - res_text.get_width()//2, HEIGHT//2 + 10))

        # 500ミリ秒（0.5秒）ごとに文字を表示したり消したりして点滅させる処理
        blink_str = "Press SPACE to Play" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        if blink_str:
            blink_text = large_font.render(blink_str, True, GRAY)
            screen.blit(blink_text, (WIDTH//2 - blink_text.get_width()//2, HEIGHT//2 + 80))

        # 背景素材サイトへのクレジット表記（画面右下）
        credit_text1 = font.render("背景素材: ゲームまてりあるず", True, GRAY)
        credit_text2 = font.render("https://game-materials.com/", True, GRAY)
        screen.blit(credit_text1, (WIDTH - credit_text1.get_width() - 10, HEIGHT - 70))
        screen.blit(credit_text2, (WIDTH - credit_text2.get_width() - 10, HEIGHT - 35))

    # ここまで裏側で作った画面を一気にモニターへ反映（更新）する
    pygame.display.flip()
    clock.tick(60) # 1秒間に60フレームで動作するように調整する

# ゲームのウィンドウが閉じられた時の終了処理
if ser is not None: ser.close() # 繋いでいたシリアルポートを綺麗に閉じる
if joystick is not None and joystick.get_init():
    joystick.quit()
pygame.quit() # Pygameを終了
sys.exit() # プログラム自体を終了