#include <M5StickC.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

int handState = 0; 
bool pcConnected = false; 
unsigned long lastPcTime = 0; 
int clearCount = 0; // ★追加：クリア回数（初期状態は0）

void updateHand() {
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);

  // ★修正: 1行を13文字以内に収めて折り返しを防止
  if (pcConnected) {
    M5.Lcd.setTextColor(GREEN, BLACK); 
    M5.Lcd.println("PC: CONNECTED"); // 13文字
  } else {
    M5.Lcd.setTextColor(ORANGE, BLACK); 
    M5.Lcd.println("PC: WAITING");   // 11文字
  }
  
  M5.Lcd.setTextColor(WHITE, BLACK);
  M5.Lcd.println("-------------");   // ハイフンを13個に減らす

  if (handState == 0) {
    pwm.setPWM(0, 0, 200);
    pwm.setPWM(1, 0, 290);
    pwm.setPWM(2, 0, 240);
    pwm.setPWM(3, 0, 280);
    pwm.setPWM(4, 0, 300);
    M5.Lcd.println("Hand: PA");
  } 
  else if (handState == 1) {
    pwm.setPWM(0, 0, 380);
    pwm.setPWM(1, 0, 370);
    pwm.setPWM(2, 0, 390);
    pwm.setPWM(3, 0, 180);
    pwm.setPWM(4, 0, 160);
    M5.Lcd.println("Hand: GU");
  } 
  else if (handState == 2) {
    pwm.setPWM(0, 0, 380);
    pwm.setPWM(1, 0, 290);
    pwm.setPWM(2, 0, 240);
    pwm.setPWM(3, 0, 180);
    pwm.setPWM(4, 0, 160);
    M5.Lcd.println("Hand: CHOKI");
  }

  // ★追加: クリア回数の表示
  M5.Lcd.setTextColor(WHITE, BLACK);
  M5.Lcd.println("-------------");
  M5.Lcd.setTextColor(YELLOW, BLACK);
  M5.Lcd.printf("Clear: %d/3\n", clearCount);
}

void setup() {
  M5.begin();
  M5.Lcd.setRotation(3);
  M5.Lcd.setTextSize(2);
  
  Wire.begin(32, 33);
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);

  updateHand();
}

void loop() {
  M5.update(); 
  bool stateChanged = false; 

  if (M5.BtnA.wasPressed()) {
    handState++; 
    if (handState > 2) {
      handState = 0; 
    }
    stateChanged = true;
  }

  if (Serial.available() > 0) {
    char c = Serial.read(); 
    
    lastPcTime = millis(); 
    
    if (!pcConnected) {
      pcConnected = true;
      stateChanged = true;
    }
    
    if (c == 'P') {
      handState = 0; 
      stateChanged = true;
    } 
    else if (c == 'G') {
      handState = 1; 
      stateChanged = true;
    } 
    else if (c == 'C') {
      handState = 2; 
      stateChanged = true;
    }
    // ★追加: 0〜3の数字が送られてきたらクリア回数を更新
    else if (c >= '0' && c <= '3') {
      clearCount = c - '0'; // 文字を数値に変換
      stateChanged = true;
    }
  }
  
  if (pcConnected && (millis() - lastPcTime > 3000)) {
    pcConnected = false;
    stateChanged = true;
  }
  
  if (stateChanged) {
    updateHand();
  }

  delay(20);
}