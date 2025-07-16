"""
サンプル計算モジュール

このモジュールは基本的な算術演算を提供します。
"""

from typing import Union

class Calculator:
    """
    基本的な計算機クラス
    
    四則演算の機能を提供します。
    """
    
    def __init__(self, name: str = "基本計算機"):
        """
        計算機を初期化します。
        
        Args:
            name: 計算機の名前
        """
        self.name = name
        self.history = []
    
    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """
        二つの数値を足し算します。
        
        Args:
            a: 第一オペランド
            b: 第二オペランド
            
        Returns:
            計算結果
        """
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """
        二つの数値を引き算します。
        
        Args:
            a: 被減数
            b: 減数
            
        Returns:
            計算結果
        """
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
    
    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """
        二つの数値を掛け算します。
        
        Args:
            a: 被乗数
            b: 乗数
            
        Returns:
            計算結果
        """
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
    
    def divide(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """
        二つの数値を割り算します。
        
        Args:
            a: 被除数
            b: 除数
            
        Returns:
            計算結果
            
        Raises:
            ZeroDivisionError: ゼロ除算の場合
        """
        if b == 0:
            raise ZeroDivisionError("ゼロで割ることはできません")
        
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
    
    def get_history(self) -> list[str]:
        """
        計算履歴を取得します。
        
        Returns:
            計算履歴のリスト
        """
        return self.history.copy()
    
    def clear_history(self):
        """計算履歴をクリアします。"""
        self.history.clear()


def power(base: Union[int, float], exponent: Union[int, float]) -> Union[int, float]:
    """
    べき乗計算を行います。
    
    Args:
        base: 底
        exponent: 指数
        
    Returns:
        計算結果
    """
    return base ** exponent


def factorial(n: int) -> int:
    """
    階乗計算を行います。
    
    Args:
        n: 階乗を計算する正の整数
        
    Returns:
        n! の値
        
    Raises:
        ValueError: nが負の数の場合
    """
    if n < 0:
        raise ValueError("階乗は非負の整数でのみ定義されます")
    
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    
    return result


if __name__ == "__main__":
    # 使用例
    calc = Calculator("テスト計算機")
    print(f"計算機名: {calc.name}")
    
    # 基本演算のテスト
    print(f"10 + 5 = {calc.add(10, 5)}")
    print(f"10 - 3 = {calc.subtract(10, 3)}")
    print(f"4 * 6 = {calc.multiply(4, 6)}")
    print(f"15 / 3 = {calc.divide(15, 3)}")
    
    # 履歴表示
    print("\n計算履歴:")
    for entry in calc.get_history():
        print(f"  {entry}")
    
    # 単体関数のテスト
    print(f"\n2^8 = {power(2, 8)}")
    print(f"5! = {factorial(5)}")