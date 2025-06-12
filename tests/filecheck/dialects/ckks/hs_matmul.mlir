// RUN: XDSL_ROUNDTRIP
// RUN: XDSL_GENERIC_ROUNDTRIP

!Z35184372121601_i64 = !mod_arith.int<35184372121601 : i64>
!Z36028797019389953_i64 = !mod_arith.int<36028797019389953 : i64>
#inverse_canonical_encoding = #lwe.inverse_canonical_encoding<scaling_factor = 0>
#key = #lwe.key<>
#modulus_chain_L1_C1 = #lwe.modulus_chain<elements = <36028797019389953 : i64, 35184372121601 : i64>, current = 1>
#ring_f64_1_x16 = #polynomial.ring<coefficientType = f64, polynomialModulus = <1 + x**16>>
!rns_L1 = !rns.rns<!Z36028797019389953_i64, !Z35184372121601_i64>
!pt = !lwe.new_lwe_plaintext<application_data = <message_type = tensor<1x16xf32>>, plaintext_space = <ring = #ring_f64_1_x16, encoding = #inverse_canonical_encoding>>
#ring_rns_L1_1_x16 = #polynomial.ring<coefficientType = !rns_L1, polynomialModulus = <1 + x**16>>
!pkey_L1 = !lwe.new_lwe_public_key<key = #key, ring = #ring_rns_L1_1_x16>
!skey_L1 = !lwe.new_lwe_secret_key<key = #key, ring = #ring_rns_L1_1_x16>
#ciphertext_space_L1 = #lwe.ciphertext_space<ring = #ring_rns_L1_1_x16, encryption_type = mix>
!ct_L1 = !lwe.new_lwe_ciphertext<application_data = <message_type = tensor<1x16xf32>>, plaintext_space = <ring = #ring_f64_1_x16, encoding = #inverse_canonical_encoding>, ciphertext_space = #ciphertext_space_L1, key = #key, modulus_chain = #modulus_chain_L1_C1>
module attributes {backend.openfhe, ckks.schemeParam = #ckks.scheme_param<logN = 13, Q = [36028797019389953, 35184372121601], P = [36028797019488257], logDefaultScale = 45>, scheme.ckks} {
  func.func @matmul(%ct: !ct_L1) -> !ct_L1 {
    %c15 = arith.constant 15 : index
    %c14 = arith.constant 14 : index
    %c13 = arith.constant 13 : index
    %c12 = arith.constant 12 : index
    %c11 = arith.constant 11 : index
    %c10 = arith.constant 10 : index
    %c9 = arith.constant 9 : index
    %c8 = arith.constant 8 : index
    %c7 = arith.constant 7 : index
    %c6 = arith.constant 6 : index
    %c5 = arith.constant 5 : index
    %c4 = arith.constant 4 : index
    %c3 = arith.constant 3 : index
    %c2 = arith.constant 2 : index
    %cst = arith.constant dense<[[0.0992246866, -0.946523189, 0.122071698, 1.58992755, 1.96434772, -0.0562853105, 0.315511167, 0.509273469, 1.22524285, -0.104814142, 1.26691663, -0.187680513, -0.458649457, -0.360774785, -0.713748395, -0.1546368]]> : tensor<1x16xf32>
    %c1 = arith.constant 1 : index
    %cst_0 = arith.constant dense<[[-0.45141533, -0.0277900472, 0.311195374, 0.18254894, -0.258809537, 0.497506738, 0.00115649134, -0.194445714, 0.158549473, 0.000000e+00, 0.310650676, -0.214976981, -0.023661999, -0.392960966, 6.472870e-01, 0.831665277]]> : tensor<1x16xf32>
    %cst_1 = arith.constant dense<[[0.186927512, 0.0578776859, -0.470207602, -0.716345906, -0.513711691, -0.948979198, -0.0841916725, 1.10566747, 0.109442748, -0.494833648, -0.209617928, 0.0450635366, 0.511211693, 0.420725167, -0.17439878, 0.23090896]]> : tensor<1x16xf32>
    %cst_2 = arith.constant dense<[[1.11323214, 0.718836427, 0.601066172, 0.868726789, -0.16672188, 0.330862075, -2.70876336, -0.0362475254, 0.0473451875, 0.51305908, 0.0366545655, -0.246530384, 1.56523979, 0.0427541137, -0.596498668, -0.189398453]]> : tensor<1x16xf32>
    %cst_3 = arith.constant dense<[[-0.661866903, -1.24268174, 0.527348399, -0.0778019726, -0.385623902, 1.74449313, 0.848621785, 1.33680928, 0.26154384, 0.480570585, -0.258321822, -0.600519955, 0.721896588, -0.035896223, 0.643704891, 0.261706442]]> : tensor<1x16xf32>
    %cst_4 = arith.constant dense<[[1.1475141, 0.938824236, -0.141457215, -0.732523918, 0.922843158, -0.114400379, -0.645231425, -0.160905048, -0.317237884, -0.547497034, 0.123686247, 0.934989273, -0.15196459, -0.0970092639, -0.148111045, 1.00754237]]> : tensor<1x16xf32>
    %cst_5 = arith.constant dense<[[-0.211862609, -0.431416899, -0.0720636546, -2.48991799, 0.427547336, -0.964258134, -0.101779692, 0.546912789, 0.233622894, -0.458309591, -0.320211202, 0.282270938, 0.0554278344, -0.555401444, 1.04437649, -0.666052341]]> : tensor<1x16xf32>
    %cst_6 = arith.constant dense<[[-1.26457107, 0.191955298, -0.543793797, 0.131586418, 1.511814, 0.240271449, -0.230641246, 0.32624355, -0.2265708, -0.148206532, -0.00554171437, 0.533514142, 0.185905829, -0.0191589147, 0.972919225, 0.562415779]]> : tensor<1x16xf32>
    %cst_7 = arith.constant dense<[[0.0226964187, 1.13260627, -0.123041019, -0.818917513, 0.142105132, -0.563671887, -0.0716918483, -0.300572067, 0.220496818, -0.195044488, -0.626607358, -0.500115216, -0.0506787896, 1.52065754, -0.488904893, 0.271623254]]> : tensor<1x16xf32>
    %cst_8 = arith.constant dense<[[-2.89954758, -0.986824989, -0.369369656, 0.545576334, 0.598540485, -0.896526813, -1.12681853E-4, 0.428382337, -0.73823446, -0.287197322, 0.139947563, 0.63514477, -1.2275182, 0.806710064, -0.205765828, -0.834818065]]> : tensor<1x16xf32>
    %cst_9 = arith.constant dense<[[0.256206632, 0.574271679, 0.555918574, -0.162624538, 0.0274777915, -0.334315628, -0.20700185, 0.197146744, 0.330806047, 0.396501184, -0.362113357, -1.26488256, 0.946358561, 0.0857260748, 0.240273148, 0.152525589]]> : tensor<1x16xf32>
    %cst_10 = arith.constant dense<[[0.588923454, 0.454489142, -1.12894738, -0.189138919, 0.49015525, -0.384786665, 0.114905454, -0.284750372, 0.286297977, -0.189009756, 1.86286163, 0.0139037305, -0.712347388, -0.243274495, -1.48157644, 6.842010e-01]]> : tensor<1x16xf32>
    %cst_11 = arith.constant dense<[[-0.667416632, 0.563138723, 0.55316484, 0.480629742, -0.392955244, 0.275448829, -0.333166063, -0.509723186, 1.58761895, -0.831791877, 0.124043159, 0.095811963, 0.598950267, 1.17313588, -0.181547076, -0.598543823]]> : tensor<1x16xf32>
    %cst_12 = arith.constant dense<[[0.60777837, 0.539456129, -0.955740272, 0.530687094, -0.9646492, -0.72272265, -0.0738262832, 0.0324916467, -0.715733826, 0.347885787, 0.246206611, -0.612099587, -2.4022584, -0.842383623, 1.52375555, -0.424889356]]> : tensor<1x16xf32>
    %cst_13 = arith.constant dense<[[0.260872364, -1.05352545, -0.208183318, -0.157960042, -0.370172888, -0.327790231, -0.249753788, 1.42427027, -0.772574305, 0.156113848, -0.0339187346, 6.086000e-01, 0.354834914, 0.0923027768, 0.042693194, -5.521950e-01]]> : tensor<1x16xf32>
    %cst_14 = arith.constant dense<[[-0.137271598, 0.0650914758, 0.181312144, 0.275503069, 0.313313752, 1.29883456, 0.48631376, 0.141853333, 0.255487353, -0.0788015499, -1.24023795, -0.185381308, 0.21442616, 0.292922527, -0.0227817241, -0.0453558639]]> : tensor<1x16xf32>
    %cst_15 = arith.constant dense<[[-0.794038355, -0.381407768, 0.454538226, 0.394202143, 0.064757444, -1.24775183, 1.07196343, 0.607029676, 0.584364653, -2.3380034, 0.161590248, -0.819893181, -0.321492225, -0.00216138293, -0.638892055, -0.441321522]]> : tensor<1x16xf32>
    %0 = mgmt.init %cst : tensor<1x16xf32>
    %1 = mgmt.init %cst_1 : tensor<1x16xf32>
    %2 = mgmt.init %cst_2 : tensor<1x16xf32>
    %3 = mgmt.init %cst_3 : tensor<1x16xf32>
    %4 = mgmt.init %cst_4 : tensor<1x16xf32>
    %5 = mgmt.init %cst_5 : tensor<1x16xf32>
    %6 = mgmt.init %cst_6 : tensor<1x16xf32>
    %7 = mgmt.init %cst_7 : tensor<1x16xf32>
    %8 = mgmt.init %cst_8 : tensor<1x16xf32>
    %9 = mgmt.init %cst_9 : tensor<1x16xf32>
    %10 = mgmt.init %cst_10 : tensor<1x16xf32>
    %11 = mgmt.init %cst_11 : tensor<1x16xf32>
    %12 = mgmt.init %cst_12 : tensor<1x16xf32>
    %13 = mgmt.init %cst_13 : tensor<1x16xf32>
    %14 = mgmt.init %cst_14 : tensor<1x16xf32>
    %15 = mgmt.init %cst_15 : tensor<1x16xf32>
    %16 = mgmt.init %cst_0 : tensor<1x16xf32>
    %pt = lwe.rlwe_encode %cst {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_16 = ckks.mul_plain %ct, %pt : (!ct_L1, !pt) -> !ct_L1
    %ct_17 = ckks.rotate %ct {offset = 1 : index} : !ct_L1
    %pt_18 = lwe.rlwe_encode %cst_1 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_19 = ckks.mul_plain %ct_17, %pt_18 : (!ct_L1, !pt) -> !ct_L1
    %ct_20 = ckks.rotate %ct {offset = 2 : index} : !ct_L1
    %pt_21 = lwe.rlwe_encode %cst_2 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_22 = ckks.mul_plain %ct_20, %pt_21 : (!ct_L1, !pt) -> !ct_L1
    %ct_23 = ckks.rotate %ct {offset = 3 : index} : !ct_L1
    %pt_24 = lwe.rlwe_encode %cst_3 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_25 = ckks.mul_plain %ct_23, %pt_24 : (!ct_L1, !pt) -> !ct_L1
    %ct_26 = ckks.rotate %ct {offset = 4 : index} : !ct_L1
    %pt_27 = lwe.rlwe_encode %cst_4 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_28 = ckks.mul_plain %ct_26, %pt_27 : (!ct_L1, !pt) -> !ct_L1
    %ct_29 = ckks.rotate %ct {offset = 5 : index} : !ct_L1
    %pt_30 = lwe.rlwe_encode %cst_5 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_31 = ckks.mul_plain %ct_29, %pt_30 : (!ct_L1, !pt) -> !ct_L1
    %ct_32 = ckks.rotate %ct {offset = 6 : index} : !ct_L1
    %pt_33 = lwe.rlwe_encode %cst_6 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_34 = ckks.mul_plain %ct_32, %pt_33 : (!ct_L1, !pt) -> !ct_L1
    %ct_35 = ckks.rotate %ct {offset = 7 : index} : !ct_L1
    %pt_36 = lwe.rlwe_encode %cst_7 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_37 = ckks.mul_plain %ct_35, %pt_36 : (!ct_L1, !pt) -> !ct_L1
    %ct_38 = ckks.rotate %ct {offset = 8 : index} : !ct_L1
    %pt_39 = lwe.rlwe_encode %cst_8 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_40 = ckks.mul_plain %ct_38, %pt_39 : (!ct_L1, !pt) -> !ct_L1
    %ct_41 = ckks.rotate %ct {offset = 9 : index} : !ct_L1
    %pt_42 = lwe.rlwe_encode %cst_9 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_43 = ckks.mul_plain %ct_41, %pt_42 : (!ct_L1, !pt) -> !ct_L1
    %ct_44 = ckks.rotate %ct {offset = 10 : index} : !ct_L1
    %pt_45 = lwe.rlwe_encode %cst_10 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_46 = ckks.mul_plain %ct_44, %pt_45 : (!ct_L1, !pt) -> !ct_L1
    %ct_47 = ckks.rotate %ct {offset = 11 : index} : !ct_L1
    %pt_48 = lwe.rlwe_encode %cst_11 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_49 = ckks.mul_plain %ct_47, %pt_48 : (!ct_L1, !pt) -> !ct_L1
    %ct_50 = ckks.rotate %ct {offset = 12 : index} : !ct_L1
    %pt_51 = lwe.rlwe_encode %cst_12 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_52 = ckks.mul_plain %ct_50, %pt_51 : (!ct_L1, !pt) -> !ct_L1
    %ct_53 = ckks.rotate %ct {offset = 13 : index} : !ct_L1
    %pt_54 = lwe.rlwe_encode %cst_13 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_55 = ckks.mul_plain %ct_53, %pt_54 : (!ct_L1, !pt) -> !ct_L1
    %ct_56 = ckks.rotate %ct {offset = 14 : index} : !ct_L1
    %pt_57 = lwe.rlwe_encode %cst_14 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_58 = ckks.mul_plain %ct_56, %pt_57 : (!ct_L1, !pt) -> !ct_L1
    %ct_59 = ckks.rotate %ct {offset = 15 : index} : !ct_L1
    %pt_60 = lwe.rlwe_encode %cst_15 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_61 = ckks.mul_plain %ct_59, %pt_60 : (!ct_L1, !pt) -> !ct_L1
    %pt_62 = lwe.rlwe_encode %cst_0 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct_63 = ckks.add_plain %ct_16, %pt_62 : (!ct_L1, !pt) -> !ct_L1
    %ct_64 = ckks.add %ct_19, %ct_22 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_65 = ckks.add %ct_63, %ct_64 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_66 = ckks.add %ct_25, %ct_28 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_67 = ckks.add %ct_31, %ct_34 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_68 = ckks.add %ct_66, %ct_67 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_69 = ckks.add %ct_65, %ct_68 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_70 = ckks.add %ct_37, %ct_40 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_71 = ckks.add %ct_43, %ct_46 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_72 = ckks.add %ct_70, %ct_71 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_73 = ckks.add %ct_49, %ct_52 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_74 = ckks.add %ct_55, %ct_58 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_75 = ckks.add %ct_74, %ct_61 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_76 = ckks.add %ct_73, %ct_75 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_77 = ckks.add %ct_72, %ct_76 : (!ct_L1, !ct_L1) -> !ct_L1
    %ct_78 = ckks.add %ct_69, %ct_77 : (!ct_L1, !ct_L1) -> !ct_L1
    return %ct_78 : !ct_L1
  }
  func.func @matmul__encrypt__arg0(%arg0: tensor<1x16xf32>, %pk: !pkey_L1) -> !ct_L1 {
    %pt = lwe.rlwe_encode %arg0 {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : tensor<1x16xf32> -> !pt
    %ct = lwe.rlwe_encrypt %pt, %pk : (!pt, !pkey_L1) -> !ct_L1
    return %ct : !ct_L1
  }
  func.func @matmul__decrypt__result0(%ct: !ct_L1, %sk: !skey_L1) -> tensor<1x16xf32> {
    %pt = lwe.rlwe_decrypt %ct, %sk : (!ct_L1, !skey_L1) -> !pt
    %0 = lwe.rlwe_decode %pt {encoding = #inverse_canonical_encoding, ring = #ring_f64_1_x16} : !pt -> tensor<1x16xf32>
    return %0 : tensor<1x16xf32>
  }
}
