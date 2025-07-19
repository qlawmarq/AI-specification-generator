# calculator 詳細設計書

## 1. 概要

-   **システム概要**
    本システムは、基本的な算術演算機能と計算履歴管理機能を提供する単一モジュールで構成されます。合計1個のクラスと13個の関数を含み、各コンポーネントは明確な責務を持ち、適切に分離された設計となっています。これにより、高い保守性と拡張性を確保しています。

-   **対象範囲（ファイル）**
    `calculator.js` (または同等の単一モジュールファイル)

-   **前提条件・制約事項**
    *   標準的なJavaScript実行環境（Node.js, ブラウザなど）で動作することを前提とします。
    *   数値計算はJavaScriptの標準的な数値型 (`Number`) の精度に依存します。
    *   ゼロ除算、空配列の平均計算など、特定の不正入力に対しては適切な例外処理またはエラー値の返却を行います。

## 2. アーキテクチャ設計

-   **システム構成図**
    本システムは単一のモジュール内に主要な`Calculator`クラスと、独立した汎用関数群で構成されます。

    ```mermaid
    classDiagram
        direction LR
        class Calculator {
            +String name
            +Array history
            +constructor(name: String)
            +add(a: Number, b: Number): Number
            +subtract(a: Number, b: Number): Number
            +multiply(a: Number, b: Number): Number
            +divide(a: Number, b: Number): Number
            +square(a: Number): Number
            +power(base: Number, exp: Number): Number
            +average(numbers: Array<Number>): Number
            +getHistory(): Array<Object>
            +clearHistory(): void
        }

        note "独立関数:\n- sumReducer(a, b)\n- factorial(n)\n- calculateFibonacci(n)" as Functions
        Calculator .. Functions : 含む
    ```

-   **処理フロー概要**
    ユーザーまたは他のモジュールからの計算要求を受け付け、`Calculator`クラスのインスタンスを介して算術演算を実行します。各演算結果は内部の計算履歴に記録され、後から参照可能です。また、独立した数学関数は、`Calculator`クラスとは独立して利用可能です。

-   **主要コンポーネント間の関係**
    *   **`Calculator`クラス**: システムの主要な計算ロジックと履歴管理を担います。インスタンス化されて利用されます。
    *   **独立関数 (`sumReducer`, `factorial`, `calculateFibonacci`)**: 特定の数学的計算機能を提供します。これらは`Calculator`クラスのメソッドとは異なり、直接呼び出して利用される汎用的な関数です。`Calculator`クラスの内部でこれらの関数を直接利用することはありませんが、モジュール全体として提供される機能の一部です。

-   **関連するファイルや処理・呼び出されるメソッド・呼び出し元のメソッド**
    *   **ファイル**: `calculator.js` (単一ファイル)
    *   **呼び出し元**: 外部のアプリケーションコードやテストコードが`Calculator`クラスのインスタンスを生成し、そのメソッドを呼び出します。また、独立関数も直接呼び出されます。
    *   **呼び出されるメソッド**: `Calculator`クラスの各メソッド（`add`, `subtract`など）が外部から呼び出されます。各メソッドは計算結果を`history`属性に記録します。

## 3. クラス・メソッド設計

### 3.1 クラス・メソッド一覧表

| クラス名/関数名 | 役割 | 主要メソッド/関数 | 備考 |
| :-------------- | :--- | :---------------- | :--- |
| Calculator      | 数値計算と履歴管理 | constructor, add, subtract... | なし |
| sumReducer      | 2数値の加算 | sumReducer | 汎用的な累積関数 |
| factorial       | 階乗の計算 | factorial | 数学関数 |
| calculateFibonacci | フィボナッチ数列計算 | calculateFibonacci | 数学関数 |

### 3.2 クラス・メソッド詳細仕様

#### クラス: `Calculator`

-   **クラス概要**
    基本的な算術演算（加算、減算、乗算、除算、平方、べき乗、平均）と、それらの計算履歴を管理する機能を提供します。単一責任原則に基づき、計算ロジックと履歴管理に特化しています。

-   **属性一覧**

| 属性名  | 型     | 初期値 | 説明                                     |
| :------ | :----- | :----- | :--------------------------------------- |
| `name`  | `String` | `""`   | 電卓インスタンスの名前                   |
| `history` | `Array<Object>` | `[]`   | 計算履歴を格納する配列。各要素は`{ operation: String, operands: Array<Number>, result: Number }`の形式。 |

-   **メソッド仕様**

    *   **`constructor(name: String)`**
        *   **引数**:
            *   `name`: `String` - 電卓インスタンスの名前。
        *   **戻り値**: なし
        *   **処理概要**: `Calculator`インスタンスを初期化し、`name`属性と空の`history`配列を設定します。
        *   **例外**: なし

    *   **`add(a: Number, b: Number)`**
        *   **引数**:
            *   `a`: `Number` - 1番目の被加数。
            *   `b`: `Number` - 2番目の被加数。
        *   **戻り値**: `Number` - 加算結果。
        *   **処理概要**: `a`と`b`を加算し、結果を返します。計算履歴に`{ operation: 'add', operands: [a, b], result: a + b }`を記録します。
        *   **例外**: なし

    *   **`subtract(a: Number, b: Number)`**
        *   **引数**:
            *   `a`: `Number` - 被減数。
            *   `b`: `Number` - 減数。
        *   **戻り値**: `Number` - 減算結果。
        *   **処理概要**: `a`から`b`を減算し、結果を返します。計算履歴に`{ operation: 'subtract', operands: [a, b], result: a - b }`を記録します。
        *   **例外**: なし

    *   **`multiply(a: Number, b: Number)`**
        *   **引数**:
            *   `a`: `Number` - 1番目の乗数。
            *   `b`: `Number` - 2番目の乗数。
        *   **戻り値**: `Number` - 乗算結果。
        *   **処理概要**: `a`と`b`を乗算し、結果を返します。計算履歴に`{ operation: 'multiply', operands: [a, b], result: a * b }`を記録します。
        *   **例外**: なし

    *   **`divide(a: Number, b: Number)`**
        *   **引数**:
            *   `a`: `Number` - 被除数。
            *   `b`: `Number` - 除数。
        *   **戻り値**: `Number` - 除算結果。
        *   **処理概要**: `a`を`b`で除算し、結果を返します。計算履歴に`{ operation: 'divide', operands: [a, b], result: a / b }`を記録します。
        *   **例外**: `b`が`0`の場合、`Error`をスローします（例: "Division by zero is not allowed."）。

    *   **`square(a: Number)`**
        *   **引数**:
            *   `a`: `Number` - 平方する数値。
        *   **戻り値**: `Number` - 平方結果。
        *   **処理概要**: `a`の平方を計算し、結果を返します。計算履歴に`{ operation: 'square', operands: [a], result: a * a }`を記録します。
        *   **例外**: なし

    *   **`power(base: Number, exp: Number)`**
        *   **引数**:
            *   `base`: `Number` - 基数。
            *   `exp`: `Number` - 指数。
        *   **戻り値**: `Number` - べき乗結果。
        *   **処理概要**: `base`を`exp`乗した結果を計算し、返します。計算履歴に`{ operation: 'power', operands: [base, exp], result: base ** exp }`を記録します。
        *   **例外**: なし

    *   **`average(numbers: Array<Number>)`**
        *   **引数**:
            *   `numbers`: `Array<Number>` - 平均を計算する数値の配列。
        *   **戻り値**: `Number` - 平均値。
        *   **処理概要**: `numbers`配列の平均値を計算し、結果を返します。計算履歴に`{ operation: 'average', operands: numbers, result: average_value }`を記録します。
        *   **例外**: `numbers`配列が空の場合、`Error`をスローします（例: "Cannot calculate average of an empty array."）。

    *   **`getHistory()`**
        *   **引数**: なし
        *   **戻り値**: `Array<Object>` - 計算履歴の配列。
        *   **処理概要**: 現在の計算履歴配列のコピーを返します。
        *   **例外**: なし

    *   **`clearHistory()`**
        *   **引数**: なし
        *   **戻り値**: なし
        *   **処理概要**: 計算履歴配列を空にします。
        *   **例外**: なし

-   **継承・実装関係**
    *   継承: なし
    *   実装: なし

#### 関数: `sumReducer(a: Number, b: Number)`

-   **関数概要**
    `Array.prototype.reduce`メソッドのコールバック関数として使用することを想定した、2つの数値を加算する汎用関数です。

-   **引数**:
    *   `a`: `Number` - 累積値。
    *   `b`: `Number` - 現在の値。
-   **戻り値**: `Number` - `a`と`b`の合計。
-   **処理概要**: `a`と`b`を加算し、その結果を返します。
-   **例外**: なし

#### 関数: `factorial(n: Number)`

-   **関数概要**
    与えられた非負整数`n`の階乗（n!）を計算します。

-   **引数**:
    *   `n`: `Number` - 階乗を計算する非負整数。
-   **戻り値**: `Number` - `n`の階乗。
-   **処理概要**: `n`が0の場合は1を返し、それ以外の場合は1から`n`までのすべての正の整数を掛け合わせた値を再帰的または反復的に計算します。
-   **例外**: `n`が負の数の場合、`Error`をスローします（例: "Factorial is not defined for negative numbers."）。

#### 関数: `calculateFibonacci(n: Number)`

-   **関数概要**
    与えられた数値`n`に対し、フィボナッチ数列の`n`番目の値を計算します。

-   **引数**:
    *   `n`: `Number` - フィボナッチ数列のインデックス（0以上の整数）。
-   **戻り値**: `Number` - フィボナッチ数列の`n`番目の値。
-   **処理概要**: フィボナッチ数列の定義（F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2) for n>1）に従い、`n`番目の値を計算します。
-   **例外**: `n`が負の数の場合、`Error`をスローします（例: "Fibonacci sequence is not defined for negative indices."）。

## 4. インターフェース設計

本システムは単一モジュールとして提供されるため、外部APIとしてのインターフェースは持ちません。代わりに、モジュールが公開するクラスと関数の利用方法がインターフェースとなります。

-   **API 仕様 (モジュール公開インターフェース)**
    *   **`Calculator`クラス**:
        *   インスタンス化: `const calc = new Calculator("MyCalc");`
        *   メソッド呼び出し: `calc.add(10, 5);`, `calc.getHistory();`
    *   **独立関数**:
        *   直接呼び出し: `sumReducer(1, 2);`, `factorial(5);`, `calculateFibonacci(10);`

-   **入出力データ形式**
    *   **入力**: 数値 (`Number`), 数値配列 (`Array<Number>`), 文字列 (`String` - 電卓名)。
    *   **出力**: 数値 (`Number`), 計算履歴オブジェクト配列 (`Array<{ operation: String, operands: Array<Number>, result: Number }>`)。

-   **エラーレスポンス仕様**
    *   **ゼロ除算**: `Calculator.prototype.divide`メソッドで除数が`0`の場合、`Error`オブジェクトをスローします。
    *   **空配列の平均**: `Calculator.prototype.average`メソッドで入力配列が空の場合、`Error`オブジェクトをスローします。
    *   **不正な入力値**: `factorial`や`calculateFibonacci`で負の数が入力された場合、`Error`オブジェクトをスローします。
    *   エラーメッセージは具体的な内容を文字列で含みます。

## 5. データ設計

-   **データ構造**
    `Calculator`クラスの`history`属性は、計算履歴を保持するための配列です。各履歴エントリは以下の構造を持つオブジェクトです。

    ```json
    {
      "operation": "add",        // 実行された演算の種類 (例: "add", "subtract", "divide", "average")
      "operands": [10, 5],       // 演算に使用されたオペランドの配列 (例: [10, 5] for add, [10] for square, [1, 2, 3] for average)
      "result": 15               // 演算結果
    }
    ```

-   **データベーステーブル設計**
    本システムはインメモリで動作し、永続的なデータストア（データベース）は使用しません。

-   **データフロー図**
    `Calculator`インスタンスにおける計算と履歴管理のデータフローを示します。

    ```mermaid
    flowchart TD
        A[ユーザー入力] --> B{Calculatorメソッド呼び出し};
        B -- 数値データ --> C[計算ロジック実行];
        C -- 計算結果 --> D[履歴データ生成];
        D --> E[history配列へ追加];
        C -- 計算結果 --> F[結果返却];
        E -- 履歴取得要求 --> G[getHistoryメソッド];
        G -- history配列コピー --> H[履歴データ返却];
    ```

## 6. 処理設計

### 6.1 主要処理フロー

`Calculator`クラスのインスタンスが生成され、計算メソッドが呼び出される際の一般的なシーケンスを示します。

-   **シーケンス図での表現**

    ```mermaid
    sequenceDiagram
        participant User
        participant ClientApp
        participant CalculatorInstance

        User->>ClientApp: 計算要求 (例: "10 + 5")
        ClientApp->>CalculatorInstance: new Calculator("MyCalc")
        activate CalculatorInstance
        CalculatorInstance-->>ClientApp: Calculatorインスタンス生成
        deactivate CalculatorInstance

        ClientApp->>CalculatorInstance: add(10, 5)
        activate CalculatorInstance
        CalculatorInstance->>CalculatorInstance: 計算 (10 + 5)
        CalculatorInstance->>CalculatorInstance: 履歴に追加 ({op: 'add', ops: [10, 5], res: 15})
        CalculatorInstance-->>ClientApp: 15 (結果返却)
        deactivate CalculatorInstance

        ClientApp->>CalculatorInstance: getHistory()
        activate CalculatorInstance
        CalculatorInstance-->>ClientApp: [{op: 'add', ops: [10, 5], res: 15}] (履歴返却)
        deactivate CalculatorInstance

        User->>ClientApp: 履歴クリア要求
        ClientApp->>CalculatorInstance: clearHistory()
        activate CalculatorInstance
        CalculatorInstance->>CalculatorInstance: 履歴配列をクリア
        CalculatorInstance-->>ClientApp: (void)
        deactivate CalculatorInstance
    ```

-   **処理ステップの詳細説明**
    1.  **インスタンス生成**:
        *   クライアントアプリケーションは、`Calculator`クラスのコンストラクタを呼び出し、新しい`Calculator`インスタンスを生成します。この際、電卓の名前を指定できます。
        *   インスタンスは内部で空の計算履歴配列を初期化します。
    2.  **計算メソッド呼び出し**:
        *   クライアントアプリケーションは、生成された`Calculator`インスタンスの`add`, `subtract`, `multiply`, `divide`, `square`, `power`, `average`などの計算メソッドを呼び出します。
        *   各メソッドは、引数として渡された数値に対して指定された演算を実行します。
        *   演算結果は、`history`配列に演算の種類、オペランド、結果を含むオブジェクトとして記録されます。
        *   演算結果は呼び出し元に返却されます。
        *   `divide`や`average`など、特定の条件下でエラーが発生する可能性のあるメソッドは、適切な`Error`をスローして呼び出し元に通知します。
    3.  **履歴取得**:
        *   クライアントアプリケーションは、`getHistory()`メソッドを呼び出すことで、これまでの計算履歴の配列を取得できます。
        *   このメソッドは、内部の`history`配列のコピーを返すため、元の履歴が外部から直接変更されることはありません（保守性）。
    4.  **履歴クリア**:
        *   クライアントアプリケーションは、`clearHistory()`メソッドを呼び出すことで、現在の計算履歴をすべて消去できます。
    5.  **独立関数の利用**:
        *   `sumReducer`, `factorial`, `calculateFibonacci`などの独立関数は、`Calculator`インスタンスとは関係なく、直接モジュールからインポートして利用できます。これにより、特定の数学的計算が必要な他のモジュールからの再利用性が高まります（拡張性）。