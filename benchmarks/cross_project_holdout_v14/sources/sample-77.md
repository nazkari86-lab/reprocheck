# Performance Results
Generated on: 27/02/2026 21:55:20


## Dictionary

| Scenario | Type | Size | RTL (ms) | Dext (ms) | Ratio % |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Add | Integer | 100 | 0,0902 | 0,0595 | 66,0% |
| Lookup | Integer | 100 | 0,0054 | 0,0095 | 175,9% |
| Add | Integer | 10000 | 4,8150 | 3,0843 | 64,1% |
| Lookup | Integer | 10000 | 0,6293 | 1,2031 | 191,2% |
| Add | Integer | 100000 | 65,3947 | 36,2402 | 55,4% |
| Lookup | Integer | 100000 | 7,7501 | 7,7434 | 99,9% |

## List

| Scenario | Type | Size | RTL (ms) | Dext (ms) | Ratio % |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Add/Populate | Object | 100 | 0,0255 | 0,0239 | 93,7% |
| Add/Populate | RecordSmall | 100 | 0,0383 | 0,0219 | 57,2% |
| Add/Populate | Currency | 100 | 0,0331 | 0,0248 | 74,9% |
| Add/Populate | Pointer | 100 | 0,0516 | 0,0222 | 43,0% |
| Add/Populate | String | 100 | 0,0408 | 0,0326 | 79,9% |
| Add/Populate | Integer | 100 | 0,0628 | 0,0554 | 88,2% |
| IndexOf | Integer | 100 | 0,0090 | 0,0005 | 5,6% |
| Iteration | Pointer | 100 | 0,0011 | 0,0029 | 263,6% |
| Iteration | Object | 100 | 0,0011 | 0,0028 | 254,5% |
| Iteration | String | 100 | 0,0036 | 0,0056 | 155,6% |
| Iteration | Integer | 100 | 0,0015 | 0,0257 | 1713,3% |
| Iteration | Currency | 100 | 0,0010 | 0,0042 | 420,0% |
| Iteration | RecordSmall | 100 | 0,0031 | 0,0034 | 109,7% |
| Remove-First | Integer | 100 | 0,0035 | 0,0064 | 182,9% |
| Remove-Last | String | 100 | 0,0047 | 0,0157 | 334,0% |
| Sort | String | 100 | 0,0297 | 0,0499 | 168,0% |
| Sort | Integer | 100 | 0,0057 | 0,0446 | 782,5% |
| Add/Populate | RecordSmall | 10000 | 0,2792 | 1,0251 | 367,2% |
| Add/Populate | Object | 10000 | 0,9063 | 0,8649 | 95,4% |
| Add/Populate | Pointer | 10000 | 0,0752 | 0,1166 | 155,1% |
| Add/Populate | Currency | 10000 | 0,0898 | 0,1750 | 194,9% |
| Add/Populate | String | 10000 | 1,3640 | 1,4060 | 103,1% |
| Add/Populate | Integer | 10000 | 0,1171 | 0,1263 | 107,9% |
| IndexOf | Integer | 10000 | 0,0068 | 0,0103 | 151,5% |
| Iteration | Integer | 10000 | 0,0497 | 0,2080 | 418,5% |
| Iteration | Pointer | 10000 | 0,0488 | 0,1691 | 346,5% |
| Iteration | String | 10000 | 0,3315 | 0,4790 | 144,5% |
| Iteration | Object | 10000 | 0,0490 | 0,1767 | 360,6% |
| Iteration | Currency | 10000 | 0,0554 | 0,2957 | 533,8% |
| Iteration | RecordSmall | 10000 | 0,2681 | 0,2331 | 86,9% |
| Remove-First | Integer | 10000 | 5,4490 | 6,3329 | 116,2% |
| Remove-Last | String | 10000 | 0,6709 | 1,4820 | 220,9% |
| Sort | Integer | 10000 | 0,7294 | 1,5955 | 218,7% |
| Sort | String | 10000 | 5,8162 | 6,4991 | 111,7% |
| Add/Populate | String | 100000 | 10,8720 | 11,7478 | 108,1% |
| Add/Populate | Currency | 100000 | 0,5735 | 2,3182 | 404,2% |
| Add/Populate | Object | 100000 | 6,9712 | 6,0824 | 87,3% |
| Add/Populate | Integer | 100000 | 0,7402 | 2,6071 | 352,2% |
| Add/Populate | Pointer | 100000 | 0,4496 | 1,1987 | 266,6% |
| Add/Populate | RecordSmall | 100000 | 4,8578 | 10,5044 | 216,2% |
| IndexOf | Integer | 100000 | 0,0690 | 0,0708 | 102,6% |
| Iteration | RecordSmall | 100000 | 1,6706 | 1,6965 | 101,6% |
| Iteration | Currency | 100000 | 0,3436 | 1,8499 | 538,4% |
| Iteration | Pointer | 100000 | 0,3019 | 1,1582 | 383,6% |
| Iteration | Object | 100000 | 0,3124 | 1,0961 | 350,9% |
| Iteration | String | 100000 | 2,2538 | 3,2110 | 142,5% |
| Iteration | Integer | 100000 | 0,4976 | 2,2146 | 445,1% |
| Remove-First | Integer | 100000 | 675,9252 | 578,0734 | 85,5% |
| Remove-Last | String | 100000 | 3,7671 | 11,2414 | 298,4% |
| Sort | String | 100000 | 44,5112 | 49,8751 | 112,1% |
| Sort | Integer | 100000 | 9,1688 | 20,6477 | 225,2% |

