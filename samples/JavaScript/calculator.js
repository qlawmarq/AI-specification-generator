/**
 * Calculator module providing basic arithmetic operations
 * 
 * This module demonstrates JavaScript features including:
 * - ES6 class syntax
 * - Arrow functions
 * - Array methods
 * - Error handling
 */

/**
 * Calculator class for basic arithmetic operations
 */
class Calculator {
    /**
     * Initialize a new Calculator instance
     * @param {string} name - Name of the calculator
     */
    constructor(name = "Basic Calculator") {
        this.name = name;
        this.history = [];
    }

    /**
     * Add two numbers
     * @param {number} a - First operand
     * @param {number} b - Second operand
     * @returns {number} Sum of a and b
     */
    add(a, b) {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }

    /**
     * Subtract two numbers
     * @param {number} a - Minuend
     * @param {number} b - Subtrahend
     * @returns {number} Difference of a and b
     */
    subtract(a, b) {
        const result = a - b;
        this.history.push(`${a} - ${b} = ${result}`);
        return result;
    }

    /**
     * Multiply two numbers
     * @param {number} a - First factor
     * @param {number} b - Second factor
     * @returns {number} Product of a and b
     */
    multiply(a, b) {
        const result = a * b;
        this.history.push(`${a} * ${b} = ${result}`);
        return result;
    }

    /**
     * Divide two numbers
     * @param {number} a - Dividend
     * @param {number} b - Divisor
     * @returns {number} Quotient of a and b
     * @throws {Error} When dividing by zero
     */
    divide(a, b) {
        if (b === 0) {
            throw new Error("Cannot divide by zero");
        }
        const result = a / b;
        this.history.push(`${a} / ${b} = ${result}`);
        return result;
    }

    /**
     * Calculate the square of a number
     * @param {number} x - Number to square
     * @returns {number} Square of x
     */
    square(x) {
        const result = x * x;
        this.history.push(`${x}² = ${result}`);
        return result;
    }

    /**
     * Calculate the power of a number
     * @param {number} base - Base number
     * @param {number} exponent - Exponent
     * @returns {number} base raised to exponent
     */
    power(base, exponent) {
        const result = Math.pow(base, exponent);
        this.history.push(`${base}^${exponent} = ${result}`);
        return result;
    }

    /**
     * Calculate the average of an array of numbers
     * @param {number[]} numbers - Array of numbers
     * @returns {number} Average value
     * @throws {Error} When array is empty
     */
    average(numbers) {
        if (numbers.length === 0) {
            throw new Error("Cannot calculate average of empty array");
        }
        const sum = numbers.reduce((acc, num) => acc + num, 0);
        const avg = sum / numbers.length;
        this.history.push(`average([${numbers.join(', ')}]) = ${avg}`);
        return avg;
    }

    /**
     * Get calculation history
     * @returns {string[]} Array of calculation history entries
     */
    getHistory() {
        return [...this.history];
    }

    /**
     * Clear calculation history
     */
    clearHistory() {
        this.history = [];
    }
}

/**
 * Calculate factorial of a number
 * @param {number} n - Non-negative integer
 * @returns {number} Factorial of n
 * @throws {Error} When n is negative
 */
function factorial(n) {
    if (n < 0) {
        throw new Error("Factorial is only defined for non-negative integers");
    }
    if (n === 0 || n === 1) {
        return 1;
    }
    let result = 1;
    for (let i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

/**
 * Calculate fibonacci number at position n
 * @param {number} n - Position in fibonacci sequence
 * @returns {number} Fibonacci number at position n
 */
const fibonacci = (n) => {
    if (n <= 1) return n;
    let prev = 0, curr = 1;
    for (let i = 2; i <= n; i++) {
        [prev, curr] = [curr, prev + curr];
    }
    return curr;
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        Calculator,
        factorial,
        fibonacci
    };
}

// Example usage
if (typeof require === 'undefined') { // Browser environment
    const calc = new Calculator("Demo Calculator");
    console.log(`Calculator: ${calc.name}`);
    
    console.log(`10 + 5 = ${calc.add(10, 5)}`);
    console.log(`20 - 8 = ${calc.subtract(20, 8)}`);
    console.log(`6 * 7 = ${calc.multiply(6, 7)}`);
    console.log(`15 / 3 = ${calc.divide(15, 3)}`);
    console.log(`8² = ${calc.square(8)}`);
    console.log(`2^10 = ${calc.power(2, 10)}`);
    console.log(`Average of [1,2,3,4,5] = ${calc.average([1, 2, 3, 4, 5])}`);
    
    console.log("\nCalculation History:");
    calc.getHistory().forEach(entry => console.log(`  ${entry}`));
    
    console.log(`\n5! = ${factorial(5)}`);
    console.log(`Fibonacci(10) = ${fibonacci(10)}`);
}