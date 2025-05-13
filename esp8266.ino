#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

const int sensorPin = A0;  // Analog Pin connected to the light sensor
const int RGWLed = D1;     // External LED flashing based on brightness
const int masterLed = D0;  // LED to indicate Master status

// 10-segment LED bar graph pins 
const int barGraphPins[] = {D2, D3, D4, D5, D6, D7, D8, D9, 3, 1}; 
const int numSegments = 10;

const char* ssid = "108 Berkeley gfiber";
const char* password = "2719173027";

WiFiUDP udp;
unsigned int localPort = 5005;
IPAddress broadcastIp(255, 255, 255, 255);  // Broadcast IP for all devices

int sensorValue = 0;
int receivedSensorValues[6] = {0};  // Array to store sensor values from swarm
int swarmIndex = 0;                 
const int swarmSize = 6;            
bool isMaster = false;
unsigned long lastBroadcastTime = 0;
unsigned long broadcastInterval = 100;

void setup() {
  Serial.begin(9600);
  pinMode(RGWLed, OUTPUT);
  pinMode(masterLed, OUTPUT);

  // Initialize the 10-segment LED bar graph pins
  for (int i = 0; i < numSegments; i++) {
    pinMode(barGraphPins[i], OUTPUT);  // Set each pin as output
  }

  // WiFi Connection
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");

  udp.begin(localPort);  // Start UDP
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastBroadcastTime >= broadcastInterval) {
    sensorValue = analogRead(sensorPin);
    int ledBrightness = map(sensorValue, 0, 1023, 0, 255);  // Scale for PWM
    analogWrite(RGWLed, ledBrightness);

    // Update the LED bar graph based on the sensor value
    int numActiveSegments = map(sensorValue, 0, 1023, 0, numSegments);  // Map to LED segments

    // Update the 10-segment LED bar graph
    for (int i = 0; i < numSegments; i++) {
      if (i < numActiveSegments) {
        digitalWrite(barGraphPins[i], HIGH);  // Turn on LED
      } else {
        digitalWrite(barGraphPins[i], LOW);   // Turn off LED
      }
    }

    // Broadcast sensor reading
    String message = String(sensorValue);
    udp.beginPacket(broadcastIp, localPort);
    udp.write(message.c_str());
    udp.endPacket();
    lastBroadcastTime = currentMillis;
  }

  // Check for incoming UDP packets
  int packetSize = udp.parsePacket();
  if (packetSize) {
    char incomingPacket[255];
    int len = udp.read(incomingPacket, packetSize);
    if (len > 0) incomingPacket[len] = '\0';

    String receivedMessage = String(incomingPacket);
    
    // Check if the message received is RESET
    if (receivedMessage == "RESET") {
      handleResetCommand();
    } else if (!receivedMessage.startsWith("MASTER,")) {
      int receivedSensorValue = receivedMessage.toInt();

      // Store received value in the array
      if (swarmIndex < swarmSize) {
        receivedSensorValues[swarmIndex] = receivedSensorValue;
        swarmIndex++;
      }

      if (swarmIndex == swarmSize) {
        processSwarmValues();
        swarmIndex = 0;  // Reset for the next cycle
      }
    }
  }

  delay(10);
}

void processSwarmValues() {
  // Find the maximum sensor value in the swarm
  int maxReceivedValue = findMaxValue(receivedSensorValues, swarmSize);

  Serial.print("Sensor Value: ");
  Serial.println(sensorValue);

  Serial.print("Maximum Received Value: ");
  Serial.println(maxReceivedValue);

  // ESP Master Check 
  if (sensorValue > maxReceivedValue) {
    isMaster = true;
    digitalWrite(masterLed, LOW);  // Turn on Master LED
    Serial.println("This ESP is the new master");
    sendDataToPi();
  } else {
    isMaster = false;
    digitalWrite(masterLed, HIGH);  // Turn off Master LED
    Serial.println("This ESP is not currently the master");
  }
}

int findMaxValue(int values[], int size) {
  int maxValue = values[0]; 
  for (int i = 1; i < size; i++) {
    if (values[i] > maxValue) {
      maxValue = values[i];
    }
  }
  return maxValue;
}

void handleResetCommand() {
  Serial.println("Received RESET command, resetting system state...");
  isMaster = false;
  digitalWrite(masterLed, HIGH);  // Turn off Master LED
}

void sendDataToPi() {
  String message = "MASTER," + String(sensorValue);
  udp.beginPacket(broadcastIp, localPort);
  udp.write(message.c_str());
  udp.endPacket();
  Serial.print("Sent MASTER message to Pi: ");
  Serial.println(message);
}
