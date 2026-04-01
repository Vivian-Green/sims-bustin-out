sims bustin' out startup sequence:

FUN_80003100 (init)
        80003100: lis r1, -0x7FC8      ; r1 = 0x80380000
        80003104: ori r1, r1, 0xF2C0  ; r1 = 0x8038F2C0
        80003108: lis r2, -0x7FC7      ; r2 = 0x80390000 - SDA2 pointer (sdata2)
        8000310c: ori r2, r2, 0x33E0  ; r2 = 0x803933E0
        80003110: lis r13, -0x7FC8     ; r13 = 0x80380000 - SDA pointer (sdata, sbss)
        80003114: ori r13, r13, 0x33E0 ; r13 = 0x803833E0
        80003118: bl FUN_80003300...

FUN_80003300 (ZeroGQRs)
        80003300 38 60 00 00     li         r3,0x0              ; zero GQR (graphics quantizer registers)
        80003304 7c 70 e3 a6     mtspr      GQR0,r3
        80003308 7c 71 e3 a6     mtspr      GQR1,r3
...
        8000331c 7c 76 e3 a6     mtspr      GQR6,r3
        80003320 7c 77 e3 a6     mtspr      GQR7,r3
        80003324 4e 80 00 20     blr

FUN_80003334 (FPUInit)
        80003334 7c 60 00 a6     mfmsr      r3                  ; read MSR (this definitely means something????????)
        80003338 60 63 20 00     ori        r3,r3,0x2000        ; enable FPU
        8000333c 7c 60 01 24     mtmsr      r3,0
        80003340 7c 78 e2 a6     mfspr      r3,HID2 
        80003344 54 63 1f ff     rlwinm.    r3,r3,0x3,0x1f,0x1f
        80003348 41 82 00 8c     beq        LAB_800033d4        ; passes over this beq
        8000334c 3c 60 80 00     lis        r3,-0x8000
        80003350 60 63 33 2c     ori        r3,r3,0x332c
        80003354 e0 03 00 00     psq_l      f0,0x0(r3)=>DAT_80003328+4,0x0,GQR0=>DAT_80003
        80003358 10 20 00 90     ps_mr      f1,f0
        8000335c 10 40 00 90     ps_mr      f2,f0
        80003360 10 60 00 90     ps_mr      f3,f0
...
        800033c8 13 a0 00 90     ps_mr      f29,f0
        800033cc 13 c0 00 90     ps_mr      f30,f0
        800033d0 13 e0 00 90     ps_mr      f31,f0              ; continues
    LAB_800033d4
        800033d4 3c 60 80 00     lis        r3,-0x8000
        800033d8 60 63 33 28     ori        r3=>DAT_80003328,r3,0x3328
        800033dc c8 03 00 00     lfd        f0,0x0(r3)=>DAT_80003328
        800033e0 fc 20 00 90     fmr        f1,f0
        800033e4 fc 40 00 90     fmr        f2,f0
        800033e8 fc 60 00 90     fmr        f3,f0
...
        80003450 ff a0 00 90     fmr        f29,f0
        80003454 ff c0 00 90     fmr        f30,f0
        80003458 ff e0 00 90     fmr        f31,f0
        8000345c fd fe 05 8e     mtfsf      0xff,f0
        80003460 4e 80 00 20     blr ; return to FUN_80003100: 80003120

FUN_80003100 (init) cont.
        80003120: bl	->0x80003468

; enables performance features by setting HID0 and HID2 bits?
FUN_80003468 (HID0 and HID2 config?) 
        80003468 7c 00 00 a6     mfmsr      r0
        8000346c 60 00 20 00     ori        r0,r0,0x2000        ; branch folding enable?
        80003470 7c 00 01 24     mtmsr      r0,0
        80003474 7f e8 02 a6     mfspr      r31,LR
        80003478 48 11 57 35     bl         FUN_80118bac

FUN_80118bac (???)
        80118bac 7c 08 02 a6     mfspr      r0,LR
        80118bb0 90 01 00 04     stw        r0,local_res4(r1)
        80118bb4 94 21 ff f8     stwu       r1,local_8(r1)
        80118bb8 4b ff f5 55     bl         FUN_8011810c
    FUN_8011810c (???)
        8011810c 7c 78 e2 a6     mfspr      r3,HID2
        80118110 4e 80 00 20     blr                            ; return to FUN_80118bac: 80118bbc
FUN_80118bac (???) cont.
        80118bbc 64 63 a0 00     oris       r3,r3,0xa000        ; branch folding enable + L2 cache? (1010-0000-0000-0000)
        80118bc0 4b ff f5 55     bl         FUN_80118114
    FUN_80118114 (???)
        80118114 7c 78 e3 a6     mtspr      HID2,r3
        80118118 4e 80 00 20     blr
FUN_80118bac (???) cont.
        80118bc4 48 00 0c 19     bl         FUN_801197dc
    FUN_801197dc (???)
        801197dc 7c 70 fa a6     mfspr      r3,HID0
        801197e0 60 63 08 00     ori        r3,r3,0x800         ; branch folding enable but again?
        801197e4 7c 70 fb a6     mtspr      HID0,r3
        801197e8 4e 80 00 20     blr

FUN_80118bac (???) cont.
        80118bc8 7c 00 04 ac     sync       0x0
        80118bcc 38 60 00 00     li         r3,0x0
        80118bd0 7c 70 e3 a6     mtspr      GQR0,r3             ; load 0 into GQRs a second time?? just in case???
        80118bd4 7c 71 e3 a6     mtspr      GQR1,r3
        80118bd8 7c 72 e3 a6     mtspr      GQR2,r3
        80118bdc 7c 73 e3 a6     mtspr      GQR3,r3
        80118be0 7c 74 e3 a6     mtspr      GQR4,r3
        80118be4 7c 75 e3 a6     mtspr      GQR5,r3
        80118be8 7c 76 e3 a6     mtspr      GQR6,r3
        80118bec 7c 77 e3 a6     mtspr      GQR7,r3
        80118bf0 80 01 00 0c     lwz        r0,local_res4(r1)
        80118bf4 38 21 00 08     addi       r1,r1,0x8
        80118bf8 7c 08 03 a6     mtspr      LR,r0
        80118bfc 4e 80 00 20     blr
FUN_80003468 (???) cont.
        8000347c 48 11 4c d9     bl         FUN_80118154

FUN_80118154 (???)                                              ; init fpu but FOR SURE this time?
        80118154 7c 60 00 a6     mfmsr      r3
        80118158 60 63 20 00     ori        r3,r3,0x2000
        8011815c 7c 60 01 24     mtmsr      r3,0
        80118160 7c 78 e2 a6     mfspr      r3,HID2
        80118164 54 63 1f ff     rlwinm.    r3,r3,0x3,0x1f,0x1f
        80118168 41 82 00 8c     beq        LAB_801181f4 ; passes
        8011816c 3c 60 80 38     lis        r3,-0x7fc8
        80118170 38 63 ce 60     subi       r3=>DAT_8037ce60,r3,0x31a0
        80118174 e0 03 00 00     psq_l      f0,0x0(r3)=>DAT_8037ce60,0x0,GQR0=>DAT_8037ce64
        80118178 10 20 00 90     ps_mr      f1,f0
        8011817c 10 40 00 90     ps_mr      f2,f0
        80118180 10 60 00 90     ps_mr      f3,f0
...
        801181e8 13 a0 00 90     ps_mr      f29,f0
        801181ec 13 c0 00 90     ps_mr      f30,f0
        801181f0 13 e0 00 90     ps_mr      f31,f0
    LAB_801181f4 
        801181f4 c8 0d 9a 78     lfd        f0,-0x6588(r13)=>DOUBLE_8037ce58
        801181f8 fc 20 00 90     fmr        f1,f0
        801181fc fc 40 00 90     fmr        f2,f0
        80118200 fc 60 00 90     fmr        f3,f0
...
        80118268 ff a0 00 90     fmr        f29,f0
        8011826c ff c0 00 90     fmr        f30,f0
        80118270 ff e0 00 90     fmr        f31,f0
        80118274 fd fe 05 8e     mtfsf      0xff,f0
        80118278 4e 80 00 20     blr                            ; return to FUN_80003468: 80003480

FUN_80003468 (???) cont.
        80003480 48 11 67 89     bl         FUN_80119c08


=========================================================================================================
FUN_80119c08 (InitCPUAThirdTimeAndAlsoSNDebugger) SKIPPED FOR IRRELEVANCY
=========================================================================================================


FUN_80003468 (???) cont.
        80003484 7f e8 03 a6     mtspr      LR,r31
        80003488 4e 80 00 20     blr

FUN_80003100 (init) cont.
        80003124 38 00 ff ff     li         r0,-0x1
        80003128 94 21 ff f8     stwu       r1,-0x8(r1)=>DAT_8038f2b8 ; alloc 8B @ r1
        8000312c 90 01 00 04     stw        r0,0x4(r1)=>DAT_8038f2bc
        80003130 90 01 00 00     stw        r0,0x0(r1)=>DAT_8038f2b8
        80003134 3c 60 80 2e     lis        r3,-0x7fd2              ; r3 = 0x802E0000
        80003138 60 63 2c 40     ori        r3,r3,0x2c40            ; OR r3 with 0x2c40: 
            ; becomes addr 0x802E2C40: start of MAIN_uninitialized0 =====================================
            ; r3 becomes param1
        8000313c 38 80 00 00     li         r4,0x0 ; param2
        80003140 3c a0 80 37     lis        r5,-0x7fc9              ;set r5 to 0x80370000
        80003144 60 a5 b3 d4     ori        r5,r5,0xb3d4            ;set r5 to 0x8037b3d4
        80003148 7c a3 28 50     subf       r5,r3,r5                ;r5 = size of MAIN_uninitialized0
            ;r5 becomes param3 in func
        8000314c 48 10 eb 2d     bl         FUN_80111c78 ; FillRegionStartingAtAWithBforSizeInBytesC()

FUN_80111c78 (FillRegionStartingAtAWithBforSizeInBytesC)
        80111c78 7c 69 1b 78     mr         r9,param_1,param_1
        80111c7c 28 05 00 03     cmplwi     param_3,0x3
        80111c80 40 81 00 68     ble        LAB_80111ce8                    ; passes
        80111c84 70 60 00 03     andi.      r0,param_1,0x3
        80111c88 40 82 00 60     bne        LAB_80111ce8                    ; passes
        80111c8c 54 84 06 3e     rlwinm     param_2,param_2,0x0,0x18,0x1f
        80111c90 7c 6b 1b 78     mr         r11,param_1,param_1
        80111c94 54 80 40 2e     rlwinm     r0,param_2,0x8,0x0,0x17
        80111c98 7c 00 23 78     or         r0,r0,param_2
        80111c9c 54 09 80 1e     rlwinm     r9,r0,0x10,0x0,0xf
        80111ca0 7c 00 4b 78     or         r0,r0,r9
        80111ca4 28 05 00 0f     cmplwi     param_3,0xf
        80111ca8 40 81 00 34     ble        LAB_80111cdc
     LAB_80111cac                                                   ; loop: memory a bunch
        80111cac 90 0b 00 00     stw        r0,0x0(r11)
        80111cb0 38 a5 ff f0     subi       param_3,param_3,0x10
        80111cb4 94 0b 00 04     stwu       r0,0x4(r11)
        80111cb8 28 05 00 0f     cmplwi     param_3,0xf             ; compare logical word immediate. <param3 (r5) > 15> -> CR
        80111cbc 94 0b 00 04     stwu       r0,0x4(r11)
        80111cc0 94 0b 00 04     stwu       r0,0x4(r11)
        80111cc4 39 6b 00 04     addi       r11,r11,0x4
        80111cc8 41 81 ff e4     bgt        LAB_80111cac            ; branch if CR: greater than, with comp on ..cb8

        80111ccc 48 00 00 10     b          LAB_80111cdc            ; handle remaining bytes probably?
     LAB_80111cd0
        80111cd0 90 0b 00 00     stw        r0,0x0(r11)
        80111cd4 38 a5 ff fc     subi       param_3,param_3,0x4
        80111cd8 39 6b 00 04     addi       r11,r11,0x4
     LAB_80111cdc 
        80111cdc 28 05 00 03     cmplwi     param_3,0x3
        80111ce0 41 81 ff f0     bgt        LAB_80111cd0
        80111ce4 7d 69 5b 78     or         r9,r11,r11
     LAB_80111ce8
        80111ce8 2c 05 00 00     cmpwi      param_3,0x0
        80111cec 38 a5 ff ff     subi       param_3,param_3,0x1
        80111cf0 4d 82 00 20     beqlr
     LAB_80111cf4
        80111cf4 98 89 00 00     stb        param_2,0x0(r9)
        80111cf8 2c 05 00 00     cmpwi      param_3,0x0
        80111cfc 39 29 00 01     addi       r9,r9,0x1
        80111d00 38 a5 ff ff     subi       param_3,param_3,0x1
        80111d04 40 82 ff f0     bne        LAB_80111cf4
        80111d08 4e 80 00 20     blr                                ; ret

FUN_80003100 (init) cont.
        80003150 3c 60 80 37     lis        r3,-0x7fc9              ; r3 = 0x80370000
        80003154 60 63 ca 20     ori        r3,r3,0xca20            ; r3 = 0x8037ca20
            ; start of MAIN_uninitialized1 ==============================================================
        80003158 38 80 00 00     li         r4,0x0                  ; fill value (param2) = 0
        8000315c 3c a0 80 37     lis        r5,-0x7fc9              ; r5 = 0x80370000
        80003160 60 a5 da 0c     ori        r5,r5,0xda0c            ; r5 = 0x8037da0c
        80003164 7c a3 28 50     subf       r5,r3,r5 ; size (param3) = 
            ; 0x8037da0c - 0x8037ca20 = 0xfec (4076 bytes)
        80003168 48 10 eb 11     bl         FUN_80111c78 ; FillRegionStartingAtAWithBforSizeInBytesC()
        8000316c 38 80 00 00     li         r4,0x0                  ; load 0 into 0x80000044
        80003170 3c a0 80 00     lis        r5,-0x8000
        80003174 90 85 00 44     stw        r4,offset DAT_80000044(r5)
        80003178 3b a0 00 00     li         r29,0x0                 ; load OSBootInfo* into r6
        8000317c 3c c0 80 00     lis        r6,-0x8000
        80003180 60 c6 00 f4     ori        r6,r6,0xf4
        80003184 80 c6 00 00     lwz        r6,0x0(r6)=>DAT_800000f4
        80003188 2c 06 00 00     cmpwi      r6,0x0                  ; if ptr exists check?
        8000318c 41 82 00 18     beq        LAB_800031a4            ; passes
        80003190 80 66 00 0c     lwz        r3,0xc(r6)              ; Checks offset 0xc from OSBootInfo*
            ; this is the console type. 0 = retail, 2 = debug, 3 = devkit
        80003194 28 03 00 02     cmplwi     r3,0x2 ; check 2 > console type (isn't debug console)
        80003198 41 80 00 0c     blt        LAB_800031a4            ; JUMPS on retail gamecube
                                                                    ;
        8000319c 48 10 69 21     bl         FUN_80109abc            ;       SKIPPED
        800031a0 3b a0 00 01     li         r29,0x1                 ;       SKIPPED
                                                                  ;/_
    LAB_800031a4
        800031a4 48 00 00 b1     bl         FUN_80003254

FUN_80003254 (RelocateModuleByOSBootInfoOffset) ; OSRelocateModule?
        80003254 3c c0 80 00     lis        r6,-0x8000
        80003258 60 c6 00 f4     ori        r6,r6,0xf4
        8000325c 80 a6 00 00     lwz        r5,0x0(r6)=>DAT_800000f4 ; r5 = OSBootInfo*
        80003260 2c 05 00 00     cmpwi      r5,0x0 
        80003264 40 82 00 10     bne        LAB_80003274 ; jump if OSBootInfo NEQ NULL
    LAB_80003268
        80003268 38 60 00 00     li         r3,0x0                  ;       SKIPPED FIRST TIME?
        8000326c 38 80 00 00     li         r4,0x0                  ;       SKIPPED FIRST TIME?
        80003270 4e 80 00 20     blr                                ;       SKIPPED FIRST TIME? RET 0, 0
    LAB_80003274
        80003274 80 c5 00 08     lwz        r6,0x8(r5)              
        80003278 2c 06 00 00     cmpwi      r6,0x0
        8000327c 41 82 ff ec     beq        LAB_80003268            ; jumps back to LAB_80003268?
            ; at least on first call. Idk if this is called again. jump to ret 0, 0
        80003280 7c c5 32 14     add        r6,r5,r6
        80003284 80 66 00 00     lwz        r3,0x0(r6)
        80003288 2c 03 00 00     cmpwi      r3,0x0
        8000328c 41 82 ff dc     beq        LAB_80003268
        80003290 38 86 00 04     addi       r4,r6,0x4
        80003294 7c 69 03 a6     mtspr      CTR,r3
    LAB_80003298
        80003298 38 c6 00 04     addi       r6,r6,0x4
        8000329c 80 e6 00 00     lwz        r7,0x0(r6)
        800032a0 7c e7 2a 14     add        r7,r7,r5
        800032a4 90 e6 00 00     stw        r7,0x0(r6)
        800032a8 42 00 ff f0     bdnz       LAB_80003298
        800032ac 3c a0 80 00     lis        r5,-0x8000
        800032b0 60 a5 00 34     ori        r5,r5,0x34
        800032b4 54 87 00 34     rlwinm     r7,r4,0x0,0x0,0x1a
        800032b8 90 e5 00 00     stw        r7,0x0(r5)=>DAT_80000034
        800032bc 4e 80 00 20     blr

FUN_80003100 (init) cont.
        800031a8 7c 7e 1b 78     or         r30,r3,r3               ; store ret of FUN_80003254 (0, 0)
        800031ac 7c 9f 23 78     or         r31,r4,r4
        800031b0 48 11 ee e5     bl         FUN_80122094

FUN_80122094 (???) ; haunted function made of weird address methods I don't like
        ; loads some pointers and a 1 into some places
        80122094 3c 80 80 00     lis        r4,-0x8000              ; set r4 to 0x80000000
        80122098 38 04 00 40     addi       r0,r4,0x40              ; set r0 to 0x80000040
        8012209c 3c 60 80 12     lis        r3,-0x7fee              ; r3 = 0x80120000
        801220a0 90 0d 9b 50     stw        r0=>DAT_80000040,-0x64b0(r13)=>DAT_8037cf30
            ; stw 0x80000040 (r0) @ 0x8037CF30 (r13)
        801220a4 38 63 21 04     addi       r3=>DAT_80122104,r3,0x2104
            ; set r3 to 0x80122104
        801220a8 3c 03 80 00     subis      r0,r3,0x8000
            ;  r0 = r3 - 0x80000000 = 0x80122104 - 0x80000000 = 0x00122104 (offset? size maybe?)
        801220ac 90 04 00 48     stw        r0,offset DAT_80000048(r4)
            ; stw 0x122104 (r4) @ 0x80000048 (r0) 
        801220b0 38 00 00 01     li         r0,0x1
        801220b4 90 0d 9b 54     stw        r0,-0x64ac(r13)=>DAT_8037cf34
            ; load 1 @ (r0) 0x8037CF34
        801220b8 4e 80 00 20     blr

FUN_80003100 (init) cont.
        800031b4 48 11 52 55     bl         FUN_80118408

FUN_80118408: OSInit from OS.c. Let's NOT touch this one more than is necessary.


=========================================================================================================
=========================================================================================================
=========================================      WILD  WEST      ==========================================
=========================================================================================================
=========================================================================================================


FUN_80003100 (init) cont.
        800031b8 3c 80 80 00     lis        r4,-0x8000
        800031bc a0 64 30 e6     lhz        r3,offset DAT_800030e6(r4)
        800031c0 70 64 80 00     andi.      r4,r3,0x8000
        800031c4 41 82 00 10     beq        LAB_800031d4
        800031c8 70 63 7f ff     andi.      r3,r3,0x7fff
        800031cc 28 03 00 01     cmplwi     r3,0x1
        800031d0 40 82 00 08     bne        LAB_800031d8
    LAB_800031d4
        800031d4 48 00 00 ed     bl         FUN_800032c0
    LAB_800031d8
        800031d8 48 00 02 8d     bl         FUN_80003464
        800031dc 7f c3 f3 78     or         r3,r30,r30
        800031e0 7f e4 fb 78     or         r4,r31,r31
        800031e4 48 00 02 81     bl         FUN_80003464
        800031e8 48 11 b1 15     bl         FUN_8011e2fc
        800031ec 2c 1d 00 00     cmpwi      r29,0x0
        800031f0 41 82 00 54     beq        LAB_80003244
        800031f4 3c 60 80 2d     lis        r3,-0x7fd3
        800031f8 60 63 36 90     ori        r3=>s_<<_libsn_version_%d_>>_802d3690,r3,0x3690  = "<< libsn version %d >>\n"
        800031fc 3c 80 80 2d     lis        r4,-0x7fd3
        80003200 60 84 36 b4     ori        r4,r4,0x36b4
        80003204 80 84 00 00     lwz        r4,0x0(r4)=>DAT_802d36b4                         = 0000003Ah
        80003208 48 11 73 95     bl         FUN_8011a59c                                     undefined FUN_8011a59c(undefined
        8000320c 3c 60 80 2d     lis        r3,-0x7fd3
        80003210 60 63 36 70     ori        r3=>s_Waiting_for_SN_Debugger..._802d3670,r3,0   = "Waiting for SN Debugger...\n"
        80003214 48 11 73 89     bl         FUN_8011a59c                                     undefined FUN_8011a59c(undefined
        80003218 7c a0 00 a6     mfmsr      r5
        8000321c 60 a4 80 00     ori        r4,r5,0x8000
        80003220 68 84 80 00     xori       r4,r4,0x8000
        80003224 7c 80 01 24     mtmsr      r4,0
        80003228 7c 00 04 ac     sync       0x0
        8000322c 60 a5 02 00     ori        r5,r5,0x200
        80003230 7c bb 03 a6     mtspr      SRR1,r5
        80003234 3c 80 80 00     lis        r4,-0x8000
        80003238 60 84 32 44     ori        r4,r4,0x3244
        8000323c 7c 9a 03 a6     mtspr      SRR0,r4
        80003240 4c 00 00 64     rfi
                             LAB_80003244                                    XREF[1]:     800031f0(j)  
        80003244 7f c3 f3 78     or         r3,r30,r30
        80003248 7f e4 fb 78     or         r4,r31,r31
        8000324c 48 16 69 c5     bl         FUN_80169c10
        80003250 48 10 d6 4c     b          FUN_8011089c ; jump to some kind of main(), most likely?


























void FUN_80003100(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4,
                 undefined8 param_5,undefined8 param_6,undefined8 param_7,undefined8 param_8)

{
  bool bVar1;
  undefined4 uVar2;
  int iVar3;
  undefined4 extraout_r4;
  byte *pbVar4;
  byte *pbVar5;
  int *in_r7;
  undefined4 *in_r8;
  undefined4 in_r9;
  undefined1 *in_r10;
  uint in_MSR;
  undefined8 uVar6;
  undefined8 extraout_f1;
  undefined8 uVar7;
  
  FUN_80003300();
  FUN_80003334();
  FUN_80003468();
  _DAT_8038f2bc = 0xffffffff;
  _DAT_8038f2b8 = 0xffffffff;
  FUN_80111c78((uint *)&DAT_802e2c40,0,0x98794);
  uVar6 = FUN_80111c78(&DAT_8037ca20,0,0xfec);
  pbVar4 = &DAT_80000000;
  DAT_80000044 = 0;
  bVar1 = false;
  pbVar5 = DAT_800000f4;
  if (DAT_800000f4 != (byte *)0x0) {
    if (1 < *(uint *)(DAT_800000f4 + 0xc)) {
      FUN_80109abc(uVar6,param_2,param_3,param_4,param_5,param_6,param_7,param_8,
                   *(uint *)(DAT_800000f4 + 0xc));
      bVar1 = true;
    }
  }
  uVar7 = FUN_80003254();
  iVar3 = (int)uVar7;
  uVar6 = FUN_80122094();
  uVar6 = FUN_80118408(extraout_f1,param_2,param_3,param_4,param_5,param_6,param_7,param_8,
                       (int)((ulonglong)uVar6 >> 0x20),(int)uVar6,pbVar4,(uint)pbVar5,in_r7,in_r8,
                       in_r9,in_r10);
  if (((DAT_800030e6 & 0x8000) == 0) || ((DAT_800030e6 & 0x7fff) == 1)) {
    FUN_800032c0(uVar6,param_2,param_3,param_4,param_5,param_6,param_7,param_8);
  }
  FUN_80003464();
  FUN_80003464();
  uVar6 = FUN_8011e2fc();
  if (bVar1) {
    uVar6 = FUN_8011a59c(uVar6,param_2,param_3,param_4,param_5,param_6,param_7,param_8,
                         s_<<_libsn_version_%d_>>_802d3690,DAT_802d36b4,pbVar4,pbVar5,in_r7,in_r8,
                         in_r9,in_r10);
    FUN_8011a59c(uVar6,param_2,param_3,param_4,param_5,param_6,param_7,param_8,
                 s_Waiting_for_SN_Debugger..._802d3670,extraout_r4,pbVar4,pbVar5,in_r7,in_r8,in_r9,
                 in_r10);
    sync(0);
    returnFromInterrupt(in_MSR & 0x9000,in_MSR | 0x200);
    return;
  }
  uVar2 = FUN_80169c10(uVar6,param_2,param_3,param_4,param_5,param_6,param_7,param_8,
                       (uint)((ulonglong)uVar7 >> 0x20),iVar3,pbVar4,(uint)pbVar5,in_r7,in_r8,in_r9,
                       in_r10);
  FUN_8011089c(uVar2,iVar3,pbVar4,pbVar5,in_r7);
  return;
}

