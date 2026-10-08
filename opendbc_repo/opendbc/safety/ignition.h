#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "opendbc/safety/can.h"

bool ignition_can = false;
uint32_t ignition_can_cnt = 0U;
bool rivian_epas_on = false;
int rivian_prndl = 1;  // 1 = Park
int prev_counter_rivian_150 = -1;
int prev_counter_rivian_152 = -1;

void ignition_can_hook(const CANPacket_t *msg) {
  if (msg->bus == 0U) {
    int len = GET_LEN(msg);

    // GM exception
    if ((msg->addr == 0x1F1U) && (len == 8)) {
      // SystemPowerMode (2=Run, 3=Crank Request)
      ignition_can = (msg->data[0] & 0x2U) != 0U;
      ignition_can_cnt = 0U;
    }

    // Rivian R1S/T GEN1 exception
    if ((msg->addr == 0x152U) && (len == 8)) {
      // 0x152 overlaps with Subaru pre-global which has this bit as the high beam
      int counter = msg->data[1] & 0xFU;  // max is only 14

      if ((counter == ((prev_counter_rivian_152 + 1) % 15)) && (prev_counter_rivian_152 != -1)) {
        // VDM_OutputSignals->VDM_EpasPowerMode
        rivian_epas_on = ((msg->data[7] >> 4U) & 0x3U) == 1U;  // VDM_EpasPowerMode_Drive_On=1
        bool in_gear = (rivian_prndl == 2) || (rivian_prndl == 3) || (rivian_prndl == 4);
        ignition_can = rivian_epas_on && in_gear;
        ignition_can_cnt = 0U;
      }
      prev_counter_rivian_152 = counter;
    }

    if ((msg->addr == 0x150U) && (len == 7)) {
      int counter = msg->data[1] & 0xFU;  // max is only 14

      if ((counter == ((prev_counter_rivian_150 + 1) % 15)) && (prev_counter_rivian_150 != -1)) {
        // VDM_PropStatus->VDM_Prndl_Status: 1=Park, 2=Reverse, 3=Neutral, 4=Drive
        rivian_prndl = msg->data[2] & 0xFU;
        bool in_gear = (rivian_prndl == 2) || (rivian_prndl == 3) || (rivian_prndl == 4);
        ignition_can = rivian_epas_on && in_gear;
        ignition_can_cnt = 0U;
      }
      prev_counter_rivian_150 = counter;
    }

    // Tesla Model 3/Y exception
    if ((msg->addr == 0x221U) && (len == 8)) {
      // 0x221 overlaps with Rivian which has random data on byte 0
      int counter = msg->data[6] >> 4;

      static int prev_counter_tesla = -1;
      if ((counter == ((prev_counter_tesla + 1) % 16)) && (prev_counter_tesla != -1)) {
        // VCFRONT_LVPowerState->VCFRONT_vehiclePowerState
        int power_state = (msg->data[0] >> 5U) & 0x3U;
        ignition_can = power_state == 0x3;  // VEHICLE_POWER_STATE_DRIVE=3
        ignition_can_cnt = 0U;
      }
      prev_counter_tesla = counter;
    }

    // Mazda exception
    if ((msg->addr == 0x9EU) && (len == 8)) {
      ignition_can = (msg->data[0] >> 5) == 0x6U;
      ignition_can_cnt = 0U;
    }

    // Volkswagen MEB exception
    if ((msg->addr == 0x3C0U) && (len == 4)) {
      int counter = msg->data[1] & 0xFU;

      static int prev_counter_vw_meb = -1;
      if ((counter == ((prev_counter_vw_meb + 1) % 16)) && (prev_counter_vw_meb != -1)) {
        // Klemmen_Status_01->ZAS_Kl_15
        ignition_can = ((msg->data[2] >> 1) & 1U) != 0U;
        ignition_can_cnt = 0U;
      }
      prev_counter_vw_meb = counter;
    }
  }

  // TODO: this is too loose, Teslas have 0x222
  // body v2 exception
  // if (((msg->bus == 0U) || (msg->bus == 2U)) && (msg->addr == 0x222U)) {
  //   ignition_can = true;
  //   ignition_can_cnt = 0U;
  // }
}
