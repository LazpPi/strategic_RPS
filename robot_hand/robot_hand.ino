#include <M5StickC.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// サーボモーター制御用のインスタンス
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// --- 状態管理用の変数 ---
int handState = 0;             // 現在の手の形 (0:パー, 1:グー, 2:チョキ)
bool pcConnected = false;      // PCとの接続状態
unsigned long lastPcTime = 0;  // 最後にPCから通信を受信した時間 (ハートビート用)
int clearCount = 0;            // プレイヤーのクリア回数 (0〜3)

/*
 * 手の形（サーボモーター）とディスプレイ表示を更新する関数
 */
void updateHand() {
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);

  // 1. PCとの接続状態の表示
  // ※ setTextSize(2) の場合、1行は最大13文字。折り返しを防ぐために文字数を調整
  if (pcConnected) {
    M5.Lcd.setTextColor(GREEN, BLACK); 
    M5.Lcd.println("PC: CONNECTED"); // 13文字
  } else {
    M5.Lcd.setTextColor(ORANGE, BLACK); 
    M5.Lcd.println("PC: WAITING");   // 11文字
  }
  
  M5.Lcd.setTextColor(WHITE, BLACK);
  M5.Lcd.println("-------------");   // 区切り線（13文字）

  // 2. ロボットハンド（サーボモーター）の駆動と現在の手の表示
  if (handState == 0) {
    // パーの角度設定
    pwm.setPWM(0, 0, 200);
    pwm.setPWM(1, 0, 290);
    pwm.setPWM(2, 0, 240);
    pwm.setPWM(3, 0, 280);
    pwm.setPWM(4, 0, 300);
    M5.Lcd.println("Hand: PA");
  } 
  else if (handState == 1) {
    // グーの角度設定
    pwm.setPWM(0, 0, 340);
    pwm.setPWM(1, 0, 370);
    pwm.setPWM(2, 0, 390);
    pwm.setPWM(3, 0, 180);
    pwm.setPWM(4, 0, 180);
    M5.Lcd.println("Hand: GU");
  } 
  else if (handState == 2) {
    // チョキの角度設定
    pwm.setPWM(0, 0, 340);
    pwm.setPWM(1, 0, 290);
    pwm.setPWM(2, 0, 240);
    pwm.setPWM(3, 0, 180);
    pwm.setPWM(4, 0, 180);
    M5.Lcd.println("Hand: CHOKI");
  }

  // 3. クリア回数の表示
  M5.Lcd.setTextColor(WHITE, BLACK);
  M5.Lcd.println("-------------");
  M5.Lcd.setTextColor(YELLOW, BLACK);
  M5.Lcd.printf("Clear: %d/3\n", clearCount);
}

void setup() {
  // M5StickCの初期化とディスプレイ設定（横向き表示）
  M5.begin();
  M5.Lcd.setRotation(3);
  M5.Lcd.setTextSize(2);
  
  // I2C通信とサーボドライバーの初期化
  Wire.begin(32, 33);
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);

  // 起動時の初期画面を描画
  updateHand();
}

void loop() {
  M5.update(); 
  bool stateChanged = false; // 画面やモーターの更新が必要かどうかのフラグ

  // --- 手動操作（Aボタン） ---
  // ボタンを押すたびに パー → グー → チョキ の順に切り替わる（テスト用）
  if (M5.BtnA.wasPressed()) {
    handState++; 
    if (handState > 2) {
      handState = 0; 
    }
    stateChanged = true;
  }

  // --- PCからのシリアル通信受信 ---
  if (Serial.available() > 0) {
    char c = Serial.read(); 
    
    // 通信を受信した時刻を記録（ハートビート更新）
    lastPcTime = millis(); 
    
    // 未接続状態から復帰した場合はフラグを立てる
    if (!pcConnected) {
      pcConnected = true;
      stateChanged = true;
    }
    
    // 受信したコマンドに応じた処理
    if (c == 'P') {
      handState = 0; // パー
      stateChanged = true;
    } 
    else if (c == 'G') {
      handState = 1; // グー
      stateChanged = true;
    } 
    else if (c == 'C') {
      handState = 2; // チョキ
      stateChanged = true;
    }
    // '0'〜'3' の数字が送られてきた場合はクリア回数を更新
    else if (c >= '0' && c <= '3') {
      clearCount = c - '0'; // 文字(char)を数値(int)に変換
      stateChanged = true;
    }
  }
  
  // --- 通信切断（タイムアウト）の検知 ---
  // 最後にPCから通信を受け取ってから3秒(3000ms)以上経過した場合、切断とみなす
  if (pcConnected && (millis() - lastPcTime > 3000)) {
    pcConnected = false;
    stateChanged = true;
  }
  
  // 状態に変化があった場合のみ、画面とモーターを更新する
  if (stateChanged) {
    updateHand();
  }

  delay(20);
}