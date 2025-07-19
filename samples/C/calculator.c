/**
 * C Calculator Implementation
 * 
 * Demonstrates C language features:
 * - Structures and function pointers
 * - Dynamic memory allocation
 * - Error handling with return codes
 * - Modular programming
 * - File I/O operations
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <errno.h>

// Constants and macros
#define MAX_HISTORY 100
#define MAX_NAME_LENGTH 50
#define PRECISION 4

// Error codes
typedef enum {
    CALC_SUCCESS = 0,
    CALC_ERROR_DIVISION_BY_ZERO = 1,
    CALC_ERROR_INVALID_INPUT = 2,
    CALC_ERROR_MEMORY_ALLOCATION = 3,
    CALC_ERROR_OVERFLOW = 4,
    CALC_ERROR_NEGATIVE_ROOT = 5
} calc_error_t;

// Operation types
typedef enum {
    OP_ADD,
    OP_SUBTRACT,
    OP_MULTIPLY,
    OP_DIVIDE,
    OP_POWER,
    OP_SQUARE,
    OP_SQRT
} operation_type_t;

// History entry structure
typedef struct {
    operation_type_t operation;
    double operands[2];
    double result;
    time_t timestamp;
} history_entry_t;

// Calculator structure
typedef struct {
    char name[MAX_NAME_LENGTH];
    int precision;
    history_entry_t history[MAX_HISTORY];
    int history_count;
    int enable_history;
} calculator_t;

// Function pointer type for binary operations
typedef calc_error_t (*binary_op_func)(double a, double b, double *result);

// Function pointer type for unary operations
typedef calc_error_t (*unary_op_func)(double a, double *result);

/**
 * Round number to specified precision
 * @param value Number to round
 * @param precision Number of decimal places
 * @return Rounded number
 */
double round_to_precision(double value, int precision) {
    double factor = pow(10.0, precision);
    return round(value * factor) / factor;
}

/**
 * Add entry to calculation history
 * @param calc Calculator instance
 * @param operation Operation type
 * @param operand1 First operand
 * @param operand2 Second operand (use 0 for unary operations)
 * @param result Operation result
 */
void add_to_history(calculator_t *calc, operation_type_t operation, 
                   double operand1, double operand2, double result) {
    if (!calc->enable_history || calc->history_count >= MAX_HISTORY) {
        return;
    }
    
    history_entry_t *entry = &calc->history[calc->history_count];
    entry->operation = operation;
    entry->operands[0] = operand1;
    entry->operands[1] = operand2;
    entry->result = result;
    entry->timestamp = time(NULL);
    calc->history_count++;
}

/**
 * Initialize calculator
 * @param calc Calculator instance to initialize
 * @param name Calculator name
 * @param precision Number of decimal places
 * @return Error code
 */
calc_error_t calculator_init(calculator_t *calc, const char *name, int precision) {
    if (!calc || !name) {
        return CALC_ERROR_INVALID_INPUT;
    }
    
    strncpy(calc->name, name, MAX_NAME_LENGTH - 1);
    calc->name[MAX_NAME_LENGTH - 1] = '\0';
    calc->precision = precision;
    calc->history_count = 0;
    calc->enable_history = 1;
    
    return CALC_SUCCESS;
}

/**
 * Add two numbers
 * @param a First operand
 * @param b Second operand
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_add(double a, double b, double *result) {
    if (!result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    *result = a + b;
    return CALC_SUCCESS;
}

/**
 * Subtract two numbers
 * @param a Minuend
 * @param b Subtrahend
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_subtract(double a, double b, double *result) {
    if (!result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    *result = a - b;
    return CALC_SUCCESS;
}

/**
 * Multiply two numbers
 * @param a First factor
 * @param b Second factor
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_multiply(double a, double b, double *result) {
    if (!result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    *result = a * b;
    return CALC_SUCCESS;
}

/**
 * Divide two numbers
 * @param a Dividend
 * @param b Divisor
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_divide(double a, double b, double *result) {
    if (!result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    if (b == 0.0) {
        return CALC_ERROR_DIVISION_BY_ZERO;
    }
    *result = a / b;
    return CALC_SUCCESS;
}

/**
 * Calculate power
 * @param base Base number
 * @param exponent Exponent
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_power(double base, double exponent, double *result) {
    if (!result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    *result = pow(base, exponent);
    if (errno == ERANGE) {
        return CALC_ERROR_OVERFLOW;
    }
    return CALC_SUCCESS;
}

/**
 * Calculate square
 * @param x Number to square
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_square(double x, double *result) {
    if (!result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    *result = x * x;
    return CALC_SUCCESS;
}

/**
 * Calculate square root
 * @param x Number to calculate square root
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_sqrt(double x, double *result) {
    if (!result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    if (x < 0.0) {
        return CALC_ERROR_NEGATIVE_ROOT;
    }
    *result = sqrt(x);
    return CALC_SUCCESS;
}

/**
 * Perform binary operation with history tracking
 * @param calc Calculator instance
 * @param a First operand
 * @param b Second operand
 * @param operation Operation type
 * @param op_func Operation function
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t perform_binary_operation(calculator_t *calc, double a, double b,
                                    operation_type_t operation, binary_op_func op_func,
                                    double *result) {
    if (!calc || !op_func || !result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    
    calc_error_t error = op_func(a, b, result);
    if (error == CALC_SUCCESS) {
        *result = round_to_precision(*result, calc->precision);
        add_to_history(calc, operation, a, b, *result);
    }
    return error;
}

/**
 * Perform unary operation with history tracking
 * @param calc Calculator instance
 * @param a Operand
 * @param operation Operation type
 * @param op_func Operation function
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t perform_unary_operation(calculator_t *calc, double a,
                                   operation_type_t operation, unary_op_func op_func,
                                   double *result) {
    if (!calc || !op_func || !result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    
    calc_error_t error = op_func(a, result);
    if (error == CALC_SUCCESS) {
        *result = round_to_precision(*result, calc->precision);
        add_to_history(calc, operation, a, 0.0, *result);
    }
    return error;
}

/**
 * Calculate average of array
 * @param numbers Array of numbers
 * @param count Number of elements
 * @param result Pointer to store result
 * @return Error code
 */
calc_error_t calc_average(const double *numbers, int count, double *result) {
    if (!numbers || count <= 0 || !result) {
        return CALC_ERROR_INVALID_INPUT;
    }
    
    double sum = 0.0;
    for (int i = 0; i < count; i++) {
        sum += numbers[i];
    }
    *result = sum / count;
    return CALC_SUCCESS;
}

/**
 * Calculate factorial
 * @param n Non-negative integer
 * @return Factorial of n, or -1 on error
 */
long long factorial(int n) {
    if (n < 0) {
        return -1;
    }
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

/**
 * Check if number is prime
 * @param n Number to check
 * @return 1 if prime, 0 if not prime or invalid
 */
int is_prime(int n) {
    if (n <= 1) return 0;
    if (n <= 3) return 1;
    if (n % 2 == 0 || n % 3 == 0) return 0;
    
    for (int i = 5; i * i <= n; i += 6) {
        if (n % i == 0 || n % (i + 2) == 0) {
            return 0;
        }
    }
    return 1;
}

/**
 * Get operation name as string
 * @param operation Operation type
 * @return Operation name
 */
const char* get_operation_name(operation_type_t operation) {
    switch (operation) {
        case OP_ADD: return "Addition";
        case OP_SUBTRACT: return "Subtraction";
        case OP_MULTIPLY: return "Multiplication";
        case OP_DIVIDE: return "Division";
        case OP_POWER: return "Power";
        case OP_SQUARE: return "Square";
        case OP_SQRT: return "Square Root";
        default: return "Unknown";
    }
}

/**
 * Print calculation history
 * @param calc Calculator instance
 */
void print_history(const calculator_t *calc) {
    if (!calc) return;
    
    printf("\nCalculation History (%d entries):\n", calc->history_count);
    for (int i = 0; i < calc->history_count; i++) {
        const history_entry_t *entry = &calc->history[i];
        char time_str[26];
        ctime_r(&entry->timestamp, time_str);
        time_str[24] = '\0'; // Remove newline
        
        printf("  %s: ", get_operation_name(entry->operation));
        if (entry->operation == OP_SQUARE || entry->operation == OP_SQRT) {
            printf("%.4f = %.4f", entry->operands[0], entry->result);
        } else {
            printf("%.4f, %.4f = %.4f", entry->operands[0], entry->operands[1], entry->result);
        }
        printf(" (at %s)\n", time_str);
    }
}

/**
 * Get error message for error code
 * @param error Error code
 * @return Error message string
 */
const char* get_error_message(calc_error_t error) {
    switch (error) {
        case CALC_SUCCESS: return "Success";
        case CALC_ERROR_DIVISION_BY_ZERO: return "Division by zero";
        case CALC_ERROR_INVALID_INPUT: return "Invalid input";
        case CALC_ERROR_MEMORY_ALLOCATION: return "Memory allocation failed";
        case CALC_ERROR_OVERFLOW: return "Numeric overflow";
        case CALC_ERROR_NEGATIVE_ROOT: return "Cannot calculate square root of negative number";
        default: return "Unknown error";
    }
}

/**
 * Clear calculation history
 * @param calc Calculator instance
 */
void clear_history(calculator_t *calc) {
    if (calc) {
        calc->history_count = 0;
    }
}

/**
 * Main function demonstrating calculator usage
 */
int main() {
    calculator_t calc;
    double result;
    calc_error_t error;
    
    // Initialize calculator
    error = calculator_init(&calc, "C Calculator", PRECISION);
    if (error != CALC_SUCCESS) {
        fprintf(stderr, "Failed to initialize calculator: %s\n", get_error_message(error));
        return 1;
    }
    
    printf("Calculator: %s\n", calc.name);
    printf("Precision: %d decimal places\n\n", calc.precision);
    
    // Perform calculations
    error = perform_binary_operation(&calc, 10.0, 5.0, OP_ADD, calc_add, &result);
    if (error == CALC_SUCCESS) {
        printf("10 + 5 = %.4f\n", result);
    }
    
    error = perform_binary_operation(&calc, 20.0, 8.0, OP_SUBTRACT, calc_subtract, &result);
    if (error == CALC_SUCCESS) {
        printf("20 - 8 = %.4f\n", result);
    }
    
    error = perform_binary_operation(&calc, 6.0, 7.0, OP_MULTIPLY, calc_multiply, &result);
    if (error == CALC_SUCCESS) {
        printf("6 * 7 = %.4f\n", result);
    }
    
    error = perform_binary_operation(&calc, 15.0, 3.0, OP_DIVIDE, calc_divide, &result);
    if (error == CALC_SUCCESS) {
        printf("15 / 3 = %.4f\n", result);
    }
    
    error = perform_unary_operation(&calc, 8.0, OP_SQUARE, calc_square, &result);
    if (error == CALC_SUCCESS) {
        printf("8² = %.4f\n", result);
    }
    
    error = perform_binary_operation(&calc, 2.0, 10.0, OP_POWER, calc_power, &result);
    if (error == CALC_SUCCESS) {
        printf("2^10 = %.4f\n", result);
    }
    
    error = perform_unary_operation(&calc, 16.0, OP_SQRT, calc_sqrt, &result);
    if (error == CALC_SUCCESS) {
        printf("√16 = %.4f\n", result);
    }
    
    // Calculate average
    double numbers[] = {1.0, 2.0, 3.0, 4.0, 5.0};
    error = calc_average(numbers, 5, &result);
    if (error == CALC_SUCCESS) {
        printf("Average of [1,2,3,4,5] = %.4f\n", round_to_precision(result, calc.precision));
    }
    
    // Display history
    print_history(&calc);
    
    // Test utility functions
    printf("\nUtility Functions:\n");
    long long fact = factorial(5);
    if (fact >= 0) {
        printf("5! = %lld\n", fact);
    }
    printf("Is 17 prime? %s\n", is_prime(17) ? "Yes" : "No");
    
    // Test error handling
    printf("\nError Handling Test:\n");
    error = perform_binary_operation(&calc, 10.0, 0.0, OP_DIVIDE, calc_divide, &result);
    if (error != CALC_SUCCESS) {
        printf("Error dividing by zero: %s\n", get_error_message(error));
    }
    
    return 0;
}