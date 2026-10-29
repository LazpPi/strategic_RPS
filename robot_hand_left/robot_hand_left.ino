//SUBです。


#include <M5Unified.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h> # モーターを動かすライブラリ

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

int handState_Left = 0; // 現在の状態 (0:パー, 1:グー, 2:チョキ)

void setup() {
  M5.begin();
  M5.Lcd.setRotation(3);
  M5.Lcd.setTextSize(2);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.println("Push B Btn!"); // 起動時のメッセージ

  Wire.begin(32, 33);
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(5000);
 
}

void loop() {
  M5.update(); // ボタン状態の読み取り（必須）

  // Bボタン（側面のM5ボタン）が押されたら
  if (M5.BtnB.wasPressed()) {
    handState_Left++; // 状態を1つ進める
    if (handState_Left > 2) {
      handState_Left = 0; // 2(チョキ)の次は0(パー)に戻る
    }

    // 画面のリセット
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);

    // 状態に合わせて形と画面表示を切り替える
    if (handState_Left == 0) {
      // パー
      pwm.setPWM(8, 0, 300);
      pwm.setPWM(9, 0, 300);
      pwm.setPWM(10, 0, 380);
      pwm.setPWM(11, 0, 200);
      pwm.setPWM(12, 0, 200);
      M5.Lcd.println("PA");
    } 
    else if (handState_Left == 1) {
      // グー
      pwm.setPWM(8, 0, 180);
      pwm.setPWM(9, 0, 200);
      pwm.setPWM(10, 0, 180);
      pwm.setPWM(11, 0, 380);
      pwm.setPWM(12, 0, 380);
      M5.Lcd.println("GU");
    } 
    else if (handState_Left == 2) {
      // チョキ
      pwm.setPWM(8, 0, 160);
      pwm.setPWM(9, 0, 380);
      pwm.setPWM(10, 0, 380);
      
      pwm.setPWM(11, 0, 400);
      pwm.setPWM(12, 0, 380);
      M5.Lcd.println("CHOKI");
    }
  }
  
  delay(20); // 少し待機（ボタンの誤作動防止）
}