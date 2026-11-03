#include <M5StickC.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h> // モーターを動かすライブラリ

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

int handState = 0; // 現在の状態 (0:パー, 1:グー, 2:チョキ)

// 手の形と画面表示を更新する関数（ボタンでも通信でも使い回せるように分離）
void updateHand() {
  // 画面のリセット
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);

  if (handState == 0) {
    // パー
    pwm.setPWM(0, 0, 200);
    pwm.setPWM(1, 0, 290);
    pwm.setPWM(2, 0, 240);
    pwm.setPWM(3, 0, 280);
    pwm.setPWM(4, 0, 300);
    M5.Lcd.println("PA");
  } 
  else if (handState == 1) {
    // グー
    pwm.setPWM(0, 0, 380);
    pwm.setPWM(1, 0, 370);
    pwm.setPWM(2, 0, 390);
    pwm.setPWM(3, 0, 180);
    pwm.setPWM(4, 0, 160);
    M5.Lcd.println("GU");
  } 
  else if (handState == 2) {
    // チョキ
    pwm.setPWM(0, 0, 380);
    pwm.setPWM(1, 0, 290);
    pwm.setPWM(2, 0, 240);
    pwm.setPWM(3, 0, 180);
    pwm.setPWM(4, 0, 160);
    M5.Lcd.println("CHOKI");
  }
}

void setup() {
  // M5.begin()の中でPCと通信するためのSerial.begin(115200)も自動で実行されます
  M5.begin();
  M5.Lcd.setRotation(3);
  M5.Lcd.setTextSize(2);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.println("Wait PC..."); // 起動時のメッセージを変更

  Wire.begin(32, 33);
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);
}

void loop() {
  M5.update(); // ボタン状態の読み取り（必須）
  bool stateChanged = false; // 手の状態が変わったかどうかを判定するフラグ

  // 1. Aボタン（正面のM5ボタン）が押されたら
  if (M5.BtnA.wasPressed()) {
    handState++; 
    if (handState > 2) {
      handState = 0; 
    }
    stateChanged = true;
  }

  // 2. PC(Python)からのシリアル通信を受信したら
  if (Serial.available() > 0) {
    char c = Serial.read(); // 送られてきた1文字を読み込む
    
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
  }
  
  // 状態に変化があった場合のみ、モーターと画面を動かす
  if (stateChanged) {
    updateHand();
  }

  delay(20); // 少し待機
}