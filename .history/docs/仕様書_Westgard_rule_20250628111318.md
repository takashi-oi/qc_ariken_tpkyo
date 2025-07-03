# Westgardルールモジュール仕様書

## 概要

`westgard_rules.py`は、臨床検査における品質管理（QC）データに対してWestgardマルチルールを適用するためのPythonモジュールです。このモジュールは、SD変換値を使用して各種Westgardルールを評価し、検査結果の品質を判定します。

## ファイル構成

```
src/models/westgard_rules.py
├── MultiRuleクラス
│   ├── __init__()
│   ├── check_duplicates()
│   ├── import_to_database()
│   ├── apply_type_specific_rules()
│   ├── evaluate_rules()
│   ├── apply_rules()
│   ├── check_consecutive_violations()
│   ├── check_range_violation()
│   └── check_consecutive_trend()
└── check_westgard_rules()関数
```

## 主要クラス・関数

### 1. MultiRuleクラス

#### 1.1 クラス概要
SD変換値を使用してWestgardマルチルールを適用するメインクラス

#### 1.2 コンストラクタ
```python
def __init__(self, type_conditions: Dict[str, List[Dict[str, Union[float, str]]]], db_connection)
```

**パラメータ:**
- `type_conditions`: QCタイプごとの条件設定辞書
- `db_connection`: データベース接続オブジェクト

**初期化処理:**
- タイプごとの条件をインスタンス変数に保存
- データベース接続をインスタンス変数に保存

#### 1.3 メソッド詳細

##### 1.3.1 check_duplicates()
**目的:** データベースの重複データをチェック

**パラメータ:**
- `data`: チェックするデータフレーム
- `table_name`: テーブル名

**戻り値:** `bool` - 重複がある場合True

**処理フロー:**
```mermaid
flowchart TD
    A[開始] --> B[データフレームの各行をループ]
    B --> C[SQLクエリ実行]
    C --> D{重複チェック}
    D -->|重複あり| E[Trueを返す]
    D -->|重複なし| F{全行チェック完了?}
    F -->|No| B
    F -->|Yes| G[Falseを返す]
    E --> H[終了]
    G --> H
```

##### 1.3.2 import_to_database()
**目的:** データをデータベースにインポート

**パラメータ:**
- `file_info`: ファイル情報データフレーム
- `ic_data`: ICデータフレーム
- `nc_data`: NCデータフレーム
- `pc_data`: PCデータフレーム

**戻り値:** `bool` - インポート成功時True

**処理フロー:**
```mermaid
flowchart TD
    A[開始] --> B[重複チェック実行]
    B --> C{重複あり?}
    C -->|Yes| D[Falseを返す]
    C -->|No| E[データインポート処理]
    E --> F{インポート成功?}
    F -->|Yes| G[Trueを返す]
    F -->|No| H[ロールバック]
    H --> I[Falseを返す]
    D --> J[終了]
    G --> J
    I --> J
```

##### 1.3.3 apply_type_specific_rules()
**目的:** 各QCタイプに固有のルールを適用

**パラメータ:**
- `qc_type`: QCタイプ（'IC', 'NC', 'PC'など）
- `sd_conversion_value`: SD変換値

**戻り値:** `Tuple[bool, str]` - (エラーの有無, エラーメッセージ)

**処理フロー:**
```mermaid
flowchart TD
    A[開始] --> B[エラーフラグ初期化]
    B --> C{QCタイプが条件に存在?}
    C -->|No| D[エラーなしで返す]
    C -->|Yes| E[条件リスト取得]
    E --> F[各条件をループ]
    F --> G{条件タイプがsd_conversion?}
    G -->|Yes| H{SD変換値が限値を超える?}
    G -->|No| I{全条件チェック完了?}
    H -->|Yes| J[エラーフラグ設定]
    H -->|No| I
    J --> I
    I -->|No| F
    I -->|Yes| K[結果を返す]
    D --> L[終了]
    K --> L
```

##### 1.3.4 evaluate_rules()
**目的:** Westgardルールを評価

**パラメータ:**
- `sd_conversions`: SD変換値のリストまたは列

**戻り値:** `dict` - 各ルールの評価結果

**評価対象ルール:**
- **1-2s**: 最新のポイントが2σ～3σの範囲
- **1-3s**: 最新のポイントが3σを超える
- **2-2s**: 直近2点が両方とも2σを超える（同方向）
- **R-4s**: 直近2点の差が4σを超える
- **4-1s**: 直近4点が全て1σを超える（同方向）
- **8x**: 直近8点が全て平均の同じ側にある

**処理フロー:**
```mermaid
flowchart TD
    A[開始] --> B[SD変換値をリストに変換]
    B --> C[結果辞書初期化]
    C --> D[1-2s, 1-3sルール評価]
    D --> E{データ数>=2?}
    E -->|Yes| F[2-2s, R-4sルール評価]
    E -->|No| G{データ数>=4?}
    F --> G
    G -->|Yes| H[4-1sルール評価]
    G -->|No| I{データ数>=8?}
    H --> I
    I -->|Yes| J[8xルール評価]
    I -->|No| K[結果を返す]
    J --> K
    K --> L[終了]
```

##### 1.3.5 apply_rules()
**目的:** QCデータにWestgardマルチルールを適用

**パラメータ:**
- `qc_data`: QCデータのリスト
- `sd_conversions`: SD変換値のリスト
- `types`: QCタイプのリスト
- `item_codes`: 項目コードのリスト
- `dye`: 色素のリスト
- `batch`: バッチのリスト
- `model`: モデルのリスト
- `date`: 日時のリスト
- `measurer`: 測定者のリスト（オプション）
- `lot_number`: ロット番号のリスト（オプション）

**戻り値:** `pd.DataFrame` - 評価結果のデータフレーム

**処理フロー:**
```mermaid
flowchart TD
    A[開始] --> B[結果リスト初期化]
    B --> C[各データポイントをループ]
    C --> D[基本情報辞書作成]
    D --> E[Westgardルール評価]
    E --> F[タイプ固有ルール適用]
    F --> G{エラーあり?}
    G -->|Yes| H[JudgmentをFailに設定]
    G -->|No| I{Westgardルール違反?}
    H --> I
    I -->|Yes| J[エラータイプ判定]
    I -->|No| K[結果をリストに追加]
    J --> L[違反ルール抽出]
    L --> M[エラータイプ設定]
    M --> K
    K --> N{全データ処理完了?}
    N -->|No| C
    N -->|Yes| O[DataFrame変換]
    O --> P[カラム順序調整]
    P --> Q[結果を返す]
    Q --> R[終了]
```

##### 1.3.6 check_consecutive_violations()
**目的:** 連続したSD違反をチェック

**パラメータ:**
- `sd_conversions`: SD変換値のリスト
- `n_consecutive`: チェックする連続回数
- `sd_limit`: SDの限値

**戻り値:** `bool` - ルール違反があればTrue

##### 1.3.7 check_range_violation()
**目的:** R4sルール違反をチェック

**パラメータ:**
- `sd_conversions`: SD変換値のリスト
- `threshold`: 閾値（通常4）

**戻り値:** `bool` - R4s違反があればTrue

##### 1.3.8 check_consecutive_trend()
**目的:** 連続したn個の測定値が平均値の同じ側にあるかをチェック

**パラメータ:**
- `sd_conversions`: SD変換値のリスト
- `n`: チェックする連続点数

**戻り値:** `bool` - 違反があればTrue

### 2. check_westgard_rules()関数

#### 2.1 関数概要
Westgardルールに基づいてQCデータをチェックする独立関数

#### 2.2 パラメータ
- `data`: チェック対象のデータフレーム
- `historical_data`: 履歴データフレーム（オプション）

#### 2.3 戻り値
`pd.DataFrame` - 評価結果のデータフレーム

#### 2.4 処理フロー
```mermaid
flowchart TD
    A[開始] --> B{Date_Timeカラム存在確認}
    B -->|存在しない| C[ValueError発生]
    B -->|存在する| D[MultiRuleインスタンス作成]
    D --> E{履歴データあり?}
    E -->|Yes| F{履歴データにDate_Timeカラム存在?}
    E -->|No| G[データをそのまま使用]
    F -->|存在しない| H[ValueError発生]
    F -->|存在する| I[履歴データと結合]
    I --> J[日時順にソート]
    J --> K[データ処理用に整形]
    G --> K
    K --> L[Westgardルール適用]
    L --> M{最新日時フィルタリング}
    M -->|成功| N[最新日時のレコードのみ抽出]
    M -->|失敗| O[元の結果をそのまま使用]
    N --> P[結果を返す]
    O --> P
    P --> Q[終了]
    C --> Q
    H --> Q
```

## Westgardルール詳細

### 1. 1-2sルール（警告ルール）
- **条件:** 最新の測定値が2σ～3σの範囲にある
- **判定:** 注意レベル
- **対応:** 次の測定値を注意深く監視

### 2. 1-3sルール（拒否ルール）
- **条件:** 最新の測定値が3σを超える
- **判定:** 偶発誤差
- **対応:** 測定を停止し、原因を調査

### 3. 2-2sルール（拒否ルール）
- **条件:** 直近2点が両方とも2σを超える（同方向）
- **判定:** 系統誤差
- **対応:** 測定を停止し、系統的エラーを調査

### 4. R-4sルール（拒否ルール）
- **条件:** 直近2点の差が4σを超える
- **判定:** 偶発誤差
- **対応:** 測定を停止し、原因を調査

### 5. 4-1sルール（拒否ルール）
- **条件:** 直近4点が全て1σを超える（同方向）
- **判定:** 系統誤差
- **対応:** 測定を停止し、系統的エラーを調査

### 6. 8xルール（拒否ルール）
- **条件:** 直近8点が全て平均の同じ側にある
- **判定:** 系統誤差
- **対応:** 測定を停止し、系統的エラーを調査

## エラータイプ分類

### 1. 偶発誤差
- 1-3sルール違反
- R-4sルール違反
- ランダムな測定エラー

### 2. 系統誤差
- 2-2sルール違反
- 4-1sルール違反
- 8xルール違反
- 測定システムの一貫した偏り

### 3. 注意
- 1-2sルール違反
- 警告レベル

## 出力データフレーム構造

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| Measurer | str | 測定者 |
| Date_Time | str | 測定日時 |
| Item_Code | str | 項目コード |
| Batch | str | バッチ番号 |
| Model | str | モデル名 |
| Judgment | str | 判定結果（Pass/Fail） |
| Error_type | str | エラータイプ（偶発誤差/系統誤差/注意/-） |
| Type_error | str | タイプ固有エラーメッセージ |
| Violated_rule | str | 違反したルール（カンマ区切り） |
| Type | str | QCタイプ |
| Dye | str | 色素 |
| Ct | float | Ct値 |
| SD_Conversion | float | SD変換値 |
| Lot_Number | str | ロット番号 |
| 1-2s | int | 1-2sルール違反フラグ（0/1） |
| 1-3s | int | 1-3sルール違反フラグ（0/1） |
| 2-2s | int | 2-2sルール違反フラグ（0/1） |
| R-4s | int | R-4sルール違反フラグ（0/1） |
| 4-1s | int | 4-1sルール違反フラグ（0/1） |
| 8x | int | 8xルール違反フラグ（0/1） |
| File_Name | str | ファイル名 |

## 依存関係

### 標準ライブラリ
- `sqlite3`: SQLiteデータベース操作
- `typing`: 型ヒント

### サードパーティライブラリ
- `numpy`: 数値計算
- `pandas`: データ操作
- `streamlit`: Webアプリケーション

## 使用例

```python
# MultiRuleクラスの使用例
type_conditions = {
    "PC": [{"Type": "sd_conversion", "value": 2.5}],
    "IC": [{"Type": "sd_conversion", "value": 3.0}]
}

multi_rule = MultiRule(type_conditions, db_connection)

# QCデータにルールを適用
results = multi_rule.apply_rules(
    qc_data=[25.5, 26.1, 24.8],
    sd_conversions=[1.2, 2.8, -0.5],
    types=["PC", "PC", "PC"],
    item_codes=["TEST001", "TEST001", "TEST001"],
    dye=["FAM", "FAM", "FAM"],
    batch=["B001", "B001", "B001"],
    model=["MODEL1", "MODEL1", "MODEL1"],
    date=["2024-01-01", "2024-01-02", "2024-01-03"]
)

# 独立関数の使用例
results_df = check_westgard_rules(data_df, historical_data_df)
```

## 注意事項

1. **データベース接続**: データベース操作を行うメソッドを使用する場合は、適切なデータベース接続が必要です。

2. **データ形式**: 入力データは指定された形式に従う必要があります。

3. **エラーハンドリング**: 各メソッドは適切なエラーハンドリングを実装していますが、予期しないエラーが発生する可能性があります。

4. **パフォーマンス**: 大量のデータを処理する場合は、メモリ使用量と処理時間に注意してください。

5. **Westgardルール**: 医療現場での使用を想定しているため、ルールの適用結果は慎重に解釈してください。

## 更新履歴

- **2024-01-XX**: 初版作成
- **2024-01-XX**: apply_rulesメソッドのパラメータ名を`dyes`から`dye`に修正 