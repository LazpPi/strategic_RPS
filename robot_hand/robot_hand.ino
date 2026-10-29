#include <M5StickC.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h> # モーターを動かすライブラリ

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

int handState = 0; // 現在の状態 (0:パー, 1:グー, 2:チョキ)

void setup() {
  M5.begin();
  M5.Lcd.setRotation(3);
  M5.Lcd.setTextSize(2);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.println("Push A Btn!"); // 起動時のメッセージ

  Wire.begin(32, 33);
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);
}

void loop() {
  M5.update(); // ボタン状態の読み取り（必須）

  // Aボタン（正面のM5ボタン）が押されたら
  if (M5.BtnA.wasPressed()) {
    handState++; // 状態を1つ進める
    if (handState > 2) {
      handState = 0; // 2(チョキ)の次は0(パー)に戻る
    }

    // 画面のリセット
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);

    // 状態に合わせて形と画面表示を切り替える
    if (handState == 0) {
      // パー
      pwm.setPWM(0, 0, 200);
      pwm.setPWM(1, 0, 320);
      pwm.setPWM(2, 0, 220);
      pwm.setPWM(3, 0, 300);
      pwm.setPWM(4, 0, 300);
      M5.Lcd.println("PA");
    } 
    else if (handState == 1) {
      // グー
      pwm.setPWM(0, 0, 380);
      pwm.setPWM(1, 0, 410);
      pwm.setPWM(2, 0, 430);
      pwm.setPWM(3, 0, 180);
      pwm.setPWM(4, 0, 160);
      M5.Lcd.println("GU");
    } 
    else if (handState == 2) {
      // チョキ
      pwm.setPWM(0, 0, 380);
      pwm.setPWM(1, 0, 320);
      pwm.setPWM(2, 0, 220);
      pwm.setPWM(3, 0, 180);
      pwm.setPWM(4, 0, 160);
      M5.Lcd.println("CHOKI");
    }
  }
  
  delay(20); // 少し待機（ボタンの誤作動防止）
}
