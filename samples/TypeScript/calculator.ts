/**
 * TypeScript Calculator Module
 * 
 * Demonstrates TypeScript features:
 * - Type annotations and interfaces
 * - Generics
 * - Enums
 * - Access modifiers
 * - Decorators (commented out for compatibility)
 */

/**
 * Operation types enum
 */
enum OperationType {
    ADD = "ADD",
    SUBTRACT = "SUBTRACT",
    MULTIPLY = "MULTIPLY",
    DIVIDE = "DIVIDE",
    POWER = "POWER",
    SQUARE = "SQUARE",
    AVERAGE = "AVERAGE"
}

/**
 * Interface for calculation history entry
 */
interface HistoryEntry {
    operation: OperationType;
    operands: number[];
    result: number;
    timestamp: Date;
}

/**
 * Interface for calculator configuration
 */
interface CalculatorConfig {
    name: string;
    precision?: number;
    enableHistory?: boolean;
}

/**
 * Generic result type
 */
type Result<T> = {
    success: boolean;
    value?: T;
    error?: string;
};

/**
 * Advanced Calculator class with TypeScript features
 */
class AdvancedCalculator {
    private name: string;
    private precision: number;
    private history: HistoryEntry[];
    private enableHistory: boolean;

    /**
     * Initialize calculator with configuration
     * @param config - Calculator configuration object
     */
    constructor(config: CalculatorConfig) {
        this.name = config.name;
        this.precision = config.precision ?? 10;
        this.enableHistory = config.enableHistory ?? true;
        this.history = [];
    }

    /**
     * Get calculator name
     */
    public getName(): string {
        return this.name;
    }

    /**
     * Round number to configured precision
     * @param value - Number to round
     * @returns Rounded number
     */
    private round(value: number): number {
        return Math.round(value * Math.pow(10, this.precision)) / Math.pow(10, this.precision);
    }

    /**
     * Add history entry
     * @param operation - Operation type
     * @param operands - Operation operands
     * @param result - Operation result
     */
    private addToHistory(operation: OperationType, operands: number[], result: number): void {
        if (this.enableHistory) {
            this.history.push({
                operation,
                operands,
                result,
                timestamp: new Date()
            });
        }
    }

    /**
     * Add two numbers
     * @param a - First number
     * @param b - Second number
     * @returns Sum of a and b
     */
    public add(a: number, b: number): number {
        const result = this.round(a + b);
        this.addToHistory(OperationType.ADD, [a, b], result);
        return result;
    }

    /**
     * Subtract two numbers
     * @param a - Minuend
     * @param b - Subtrahend
     * @returns Difference
     */
    public subtract(a: number, b: number): number {
        const result = this.round(a - b);
        this.addToHistory(OperationType.SUBTRACT, [a, b], result);
        return result;
    }

    /**
     * Multiply two numbers
     * @param a - First factor
     * @param b - Second factor
     * @returns Product
     */
    public multiply(a: number, b: number): number {
        const result = this.round(a * b);
        this.addToHistory(OperationType.MULTIPLY, [a, b], result);
        return result;
    }

    /**
     * Divide two numbers with error handling
     * @param a - Dividend
     * @param b - Divisor
     * @returns Result object with value or error
     */
    public divide(a: number, b: number): Result<number> {
        if (b === 0) {
            return {
                success: false,
                error: "Division by zero"
            };
        }
        const result = this.round(a / b);
        this.addToHistory(OperationType.DIVIDE, [a, b], result);
        return {
            success: true,
            value: result
        };
    }

    /**
     * Calculate square of a number
     * @param x - Number to square
     * @returns Square of x
     */
    public square(x: number): number {
        const result = this.round(x * x);
        this.addToHistory(OperationType.SQUARE, [x], result);
        return result;
    }

    /**
     * Calculate power
     * @param base - Base number
     * @param exponent - Exponent
     * @returns Result
     */
    public power(base: number, exponent: number): number {
        const result = this.round(Math.pow(base, exponent));
        this.addToHistory(OperationType.POWER, [base, exponent], result);
        return result;
    }

    /**
     * Calculate average of numbers
     * @param numbers - Array of numbers
     * @returns Result with average or error
     */
    public average(numbers: number[]): Result<number> {
        if (numbers.length === 0) {
            return {
                success: false,
                error: "Cannot calculate average of empty array"
            };
        }
        const sum = numbers.reduce((acc, num) => acc + num, 0);
        const result = this.round(sum / numbers.length);
        this.addToHistory(OperationType.AVERAGE, numbers, result);
        return {
            success: true,
            value: result
        };
    }

    /**
     * Get calculation history
     * @returns Copy of history entries
     */
    public getHistory(): HistoryEntry[] {
        return [...this.history];
    }

    /**
     * Clear history
     */
    public clearHistory(): void {
        this.history = [];
    }

    /**
     * Get history summary
     * @returns Summary statistics
     */
    public getHistorySummary(): { total: number; byOperation: Record<string, number> } {
        const summary = {
            total: this.history.length,
            byOperation: {} as Record<string, number>
        };

        this.history.forEach(entry => {
            summary.byOperation[entry.operation] = (summary.byOperation[entry.operation] || 0) + 1;
        });

        return summary;
    }
}

/**
 * Generic math utility functions
 */
class MathUtils {
    /**
     * Generic factorial function
     * @param n - Non-negative integer
     * @returns Factorial of n
     */
    static factorial(n: number): number {
        if (n < 0) {
            throw new Error("Factorial is only defined for non-negative integers");
        }
        if (n === 0 || n === 1) {
            return 1;
        }
        return n * this.factorial(n - 1);
    }

    /**
     * Check if number is prime
     * @param n - Number to check
     * @returns True if prime
     */
    static isPrime(n: number): boolean {
        if (n <= 1) return false;
        if (n <= 3) return true;
        if (n % 2 === 0 || n % 3 === 0) return false;
        
        for (let i = 5; i * i <= n; i += 6) {
            if (n % i === 0 || n % (i + 2) === 0) {
                return false;
            }
        }
        return true;
    }

    /**
     * Generate fibonacci sequence
     * @param length - Length of sequence
     * @returns Array of fibonacci numbers
     */
    static fibonacciSequence(length: number): number[] {
        if (length <= 0) return [];
        if (length === 1) return [0];
        
        const sequence: number[] = [0, 1];
        for (let i = 2; i < length; i++) {
            sequence.push(sequence[i - 1] + sequence[i - 2]);
        }
        return sequence;
    }
}

// Export types and classes
export {
    AdvancedCalculator,
    MathUtils,
    CalculatorConfig,
    HistoryEntry,
    OperationType,
    Result
};

// Example usage
if (require.main === module) {
    const calc = new AdvancedCalculator({
        name: "TypeScript Calculator",
        precision: 4,
        enableHistory: true
    });

    console.log(`Calculator: ${calc.getName()}`);
    
    // Basic operations
    console.log(`10 + 5 = ${calc.add(10, 5)}`);
    console.log(`20 - 8 = ${calc.subtract(20, 8)}`);
    console.log(`6 * 7 = ${calc.multiply(6, 7)}`);
    
    // Division with error handling
    const divResult = calc.divide(15, 3);
    if (divResult.success) {
        console.log(`15 / 3 = ${divResult.value}`);
    }
    
    // More operations
    console.log(`8² = ${calc.square(8)}`);
    console.log(`2^10 = ${calc.power(2, 10)}`);
    
    // Average with error handling
    const avgResult = calc.average([1, 2, 3, 4, 5]);
    if (avgResult.success) {
        console.log(`Average of [1,2,3,4,5] = ${avgResult.value}`);
    }
    
    // History summary
    const summary = calc.getHistorySummary();
    console.log(`\nTotal operations: ${summary.total}`);
    console.log("Operations by type:", summary.byOperation);
    
    // Math utilities
    console.log(`\n5! = ${MathUtils.factorial(5)}`);
    console.log(`Is 17 prime? ${MathUtils.isPrime(17)}`);
    console.log(`First 10 Fibonacci numbers: ${MathUtils.fibonacciSequence(10).join(', ')}`);
}