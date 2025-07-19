/**
 * Java Calculator Implementation
 * 
 * Demonstrates Java features:
 * - OOP concepts (inheritance, encapsulation, polymorphism)
 * - Interfaces and abstract classes
 * - Exception handling
 * - Generics
 * - Collections framework
 * - Javadoc documentation
 */

import java.util.*;
import java.time.LocalDateTime;
import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Interface defining basic calculator operations
 */
interface CalculatorOperations {
    /**
     * Add two numbers
     * @param a first operand
     * @param b second operand
     * @return sum of a and b
     */
    double add(double a, double b);
    
    /**
     * Subtract two numbers
     * @param a minuend
     * @param b subtrahend
     * @return difference of a and b
     */
    double subtract(double a, double b);
    
    /**
     * Multiply two numbers
     * @param a first factor
     * @param b second factor
     * @return product of a and b
     */
    double multiply(double a, double b);
    
    /**
     * Divide two numbers
     * @param a dividend
     * @param b divisor
     * @return quotient of a and b
     * @throws ArithmeticException if divisor is zero
     */
    double divide(double a, double b) throws ArithmeticException;
}

/**
 * Enumeration for operation types
 */
enum OperationType {
    ADD("Addition"),
    SUBTRACT("Subtraction"), 
    MULTIPLY("Multiplication"),
    DIVIDE("Division"),
    POWER("Power"),
    SQUARE("Square"),
    SQRT("Square Root");
    
    private final String description;
    
    OperationType(String description) {
        this.description = description;
    }
    
    public String getDescription() {
        return description;
    }
}

/**
 * Class representing a calculation history entry
 */
class HistoryEntry {
    private final OperationType operation;
    private final List<Double> operands;
    private final double result;
    private final LocalDateTime timestamp;
    
    /**
     * Constructor for history entry
     * @param operation type of operation
     * @param operands list of operands
     * @param result calculation result
     */
    public HistoryEntry(OperationType operation, List<Double> operands, double result) {
        this.operation = operation;
        this.operands = new ArrayList<>(operands);
        this.result = result;
        this.timestamp = LocalDateTime.now();
    }
    
    // Getters
    public OperationType getOperation() { return operation; }
    public List<Double> getOperands() { return new ArrayList<>(operands); }
    public double getResult() { return result; }
    public LocalDateTime getTimestamp() { return timestamp; }
    
    @Override
    public String toString() {
        return String.format("%s: %s = %.4f (at %s)", 
            operation.getDescription(), 
            operands, 
            result, 
            timestamp.toString().substring(0, 19));
    }
}

/**
 * Custom exception for calculator errors
 */
class CalculatorException extends Exception {
    public CalculatorException(String message) {
        super(message);
    }
    
    public CalculatorException(String message, Throwable cause) {
        super(message, cause);
    }
}

/**
 * Abstract base calculator class
 */
abstract class BaseCalculator {
    protected String name;
    protected int precision;
    
    public BaseCalculator(String name, int precision) {
        this.name = name;
        this.precision = precision;
    }
    
    /**
     * Round number to specified precision
     * @param value number to round
     * @return rounded number
     */
    protected double round(double value) {
        BigDecimal bd = BigDecimal.valueOf(value);
        bd = bd.setScale(precision, RoundingMode.HALF_UP);
        return bd.doubleValue();
    }
    
    public String getName() { return name; }
    public int getPrecision() { return precision; }
}

/**
 * Main calculator class implementing basic operations
 */
public class Calculator extends BaseCalculator implements CalculatorOperations {
    private List<HistoryEntry> history;
    private boolean enableHistory;
    
    /**
     * Default constructor
     */
    public Calculator() {
        this("Basic Calculator", 4);
    }
    
    /**
     * Constructor with name
     * @param name calculator name
     */
    public Calculator(String name) {
        this(name, 4);
    }
    
    /**
     * Full constructor
     * @param name calculator name
     * @param precision decimal precision
     */
    public Calculator(String name, int precision) {
        super(name, precision);
        this.history = new ArrayList<>();
        this.enableHistory = true;
    }
    
    /**
     * Add to calculation history
     * @param operation type of operation
     * @param operands list of operands
     * @param result calculation result
     */
    private void addToHistory(OperationType operation, List<Double> operands, double result) {
        if (enableHistory) {
            history.add(new HistoryEntry(operation, operands, result));
        }
    }
    
    @Override
    public double add(double a, double b) {
        double result = round(a + b);
        addToHistory(OperationType.ADD, Arrays.asList(a, b), result);
        return result;
    }
    
    @Override
    public double subtract(double a, double b) {
        double result = round(a - b);
        addToHistory(OperationType.SUBTRACT, Arrays.asList(a, b), result);
        return result;
    }
    
    @Override
    public double multiply(double a, double b) {
        double result = round(a * b);
        addToHistory(OperationType.MULTIPLY, Arrays.asList(a, b), result);
        return result;
    }
    
    @Override
    public double divide(double a, double b) throws ArithmeticException {
        if (b == 0) {
            throw new ArithmeticException("Division by zero");
        }
        double result = round(a / b);
        addToHistory(OperationType.DIVIDE, Arrays.asList(a, b), result);
        return result;
    }
    
    /**
     * Calculate square of a number
     * @param x number to square
     * @return square of x
     */
    public double square(double x) {
        double result = round(x * x);
        addToHistory(OperationType.SQUARE, Arrays.asList(x), result);
        return result;
    }
    
    /**
     * Calculate power
     * @param base base number
     * @param exponent exponent
     * @return base raised to exponent
     */
    public double power(double base, double exponent) {
        double result = round(Math.pow(base, exponent));
        addToHistory(OperationType.POWER, Arrays.asList(base, exponent), result);
        return result;
    }
    
    /**
     * Calculate square root
     * @param x number to calculate square root
     * @return square root of x
     * @throws CalculatorException if x is negative
     */
    public double sqrt(double x) throws CalculatorException {
        if (x < 0) {
            throw new CalculatorException("Cannot calculate square root of negative number");
        }
        double result = round(Math.sqrt(x));
        addToHistory(OperationType.SQRT, Arrays.asList(x), result);
        return result;
    }
    
    /**
     * Calculate average of numbers
     * @param numbers array of numbers
     * @return average value
     * @throws CalculatorException if array is empty
     */
    public double average(double... numbers) throws CalculatorException {
        if (numbers.length == 0) {
            throw new CalculatorException("Cannot calculate average of empty array");
        }
        double sum = 0;
        for (double num : numbers) {
            sum += num;
        }
        return round(sum / numbers.length);
    }
    
    /**
     * Get calculation history
     * @return copy of history list
     */
    public List<HistoryEntry> getHistory() {
        return new ArrayList<>(history);
    }
    
    /**
     * Clear calculation history
     */
    public void clearHistory() {
        history.clear();
    }
    
    /**
     * Get history summary
     * @return map of operation types to counts
     */
    public Map<OperationType, Integer> getHistorySummary() {
        Map<OperationType, Integer> summary = new EnumMap<>(OperationType.class);
        for (HistoryEntry entry : history) {
            summary.merge(entry.getOperation(), 1, Integer::sum);
        }
        return summary;
    }
    
    /**
     * Enable or disable history tracking
     * @param enable true to enable, false to disable
     */
    public void setHistoryEnabled(boolean enable) {
        this.enableHistory = enable;
    }
}

/**
 * Utility class for advanced mathematical operations
 */
class MathUtils {
    /**
     * Calculate factorial
     * @param n non-negative integer
     * @return factorial of n
     * @throws IllegalArgumentException if n is negative
     */
    public static long factorial(int n) {
        if (n < 0) {
            throw new IllegalArgumentException("Factorial is only defined for non-negative integers");
        }
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    }
    
    /**
     * Check if number is prime
     * @param n number to check
     * @return true if prime, false otherwise
     */
    public static boolean isPrime(int n) {
        if (n <= 1) return false;
        if (n <= 3) return true;
        if (n % 2 == 0 || n % 3 == 0) return false;
        
        for (int i = 5; i * i <= n; i += 6) {
            if (n % i == 0 || n % (i + 2) == 0) {
                return false;
            }
        }
        return true;
    }
    
    /**
     * Generate fibonacci sequence
     * @param length length of sequence
     * @return list of fibonacci numbers
     */
    public static List<Integer> fibonacciSequence(int length) {
        List<Integer> sequence = new ArrayList<>();
        if (length <= 0) return sequence;
        
        if (length >= 1) sequence.add(0);
        if (length >= 2) sequence.add(1);
        
        for (int i = 2; i < length; i++) {
            int next = sequence.get(i - 1) + sequence.get(i - 2);
            sequence.add(next);
        }
        return sequence;
    }
}

/**
 * Main class for demonstration
 */
class CalculatorDemo {
    public static void main(String[] args) {
        Calculator calc = new Calculator("Java Calculator", 4);
        
        System.out.println("Calculator: " + calc.getName());
        System.out.println("Precision: " + calc.getPrecision() + " decimal places");
        System.out.println();
        
        try {
            // Basic operations
            System.out.println("10 + 5 = " + calc.add(10, 5));
            System.out.println("20 - 8 = " + calc.subtract(20, 8));
            System.out.println("6 * 7 = " + calc.multiply(6, 7));
            System.out.println("15 / 3 = " + calc.divide(15, 3));
            System.out.println("8² = " + calc.square(8));
            System.out.println("2^10 = " + calc.power(2, 10));
            System.out.println("√16 = " + calc.sqrt(16));
            System.out.println("Average of 1,2,3,4,5 = " + calc.average(1, 2, 3, 4, 5));
            
            // History
            System.out.println("\nCalculation History:");
            for (HistoryEntry entry : calc.getHistory()) {
                System.out.println("  " + entry);
            }
            
            // History summary
            System.out.println("\nHistory Summary:");
            Map<OperationType, Integer> summary = calc.getHistorySummary();
            for (Map.Entry<OperationType, Integer> entry : summary.entrySet()) {
                System.out.println("  " + entry.getKey().getDescription() + ": " + entry.getValue());
            }
            
            // Math utilities
            System.out.println("\nMath Utilities:");
            System.out.println("5! = " + MathUtils.factorial(5));
            System.out.println("Is 17 prime? " + MathUtils.isPrime(17));
            System.out.println("First 10 Fibonacci numbers: " + MathUtils.fibonacciSequence(10));
            
        } catch (ArithmeticException | CalculatorException e) {
            System.err.println("Error: " + e.getMessage());
        }
    }
}