/**
 * C++ Calculator Implementation
 * 
 * Demonstrates C++ features:
 * - Object-oriented programming (classes, inheritance, polymorphism)
 * - Templates and generic programming
 * - STL containers and algorithms
 * - Exception handling
 * - Operator overloading
 * - Smart pointers
 * - Lambda functions
 */

#include <iostream>
#include <vector>
#include <memory>
#include <stdexcept>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <iomanip>
#include <chrono>
#include <string>
#include <map>
#include <functional>

namespace Calculator {

/**
 * Custom exception class for calculator errors
 */
class CalculatorException : public std::runtime_error {
public:
    explicit CalculatorException(const std::string& message) 
        : std::runtime_error("Calculator Error: " + message) {}
};

/**
 * Enumeration for operation types
 */
enum class OperationType {
    ADD,
    SUBTRACT,
    MULTIPLY,
    DIVIDE,
    POWER,
    SQUARE,
    SQRT,
    AVERAGE
};

/**
 * Template class for calculation history entry
 */
template<typename T>
class HistoryEntry {
private:
    OperationType operation_;
    std::vector<T> operands_;
    T result_;
    std::chrono::system_clock::time_point timestamp_;
    
public:
    HistoryEntry(OperationType op, const std::vector<T>& operands, T result)
        : operation_(op), operands_(operands), result_(result), 
          timestamp_(std::chrono::system_clock::now()) {}
    
    // Getters
    OperationType getOperation() const { return operation_; }
    const std::vector<T>& getOperands() const { return operands_; }
    T getResult() const { return result_; }
    std::chrono::system_clock::time_point getTimestamp() const { return timestamp_; }
    
    std::string toString() const {
        std::string op_name = getOperationName(operation_);
        std::string operands_str = "[";
        for (size_t i = 0; i < operands_.size(); ++i) {
            if (i > 0) operands_str += ", ";
            operands_str += std::to_string(operands_[i]);
        }
        operands_str += "]";
        
        return op_name + ": " + operands_str + " = " + std::to_string(result_);
    }
    
private:
    std::string getOperationName(OperationType op) const {
        static const std::map<OperationType, std::string> names = {
            {OperationType::ADD, "Addition"},
            {OperationType::SUBTRACT, "Subtraction"},
            {OperationType::MULTIPLY, "Multiplication"},
            {OperationType::DIVIDE, "Division"},
            {OperationType::POWER, "Power"},
            {OperationType::SQUARE, "Square"},
            {OperationType::SQRT, "Square Root"},
            {OperationType::AVERAGE, "Average"}
        };
        auto it = names.find(op);
        return (it != names.end()) ? it->second : "Unknown";
    }
};

/**
 * Abstract base class for calculator operations
 */
template<typename T>
class CalculatorBase {
protected:
    std::string name_;
    int precision_;
    std::vector<HistoryEntry<T>> history_;
    bool enable_history_;
    
public:
    CalculatorBase(const std::string& name, int precision = 4)
        : name_(name), precision_(precision), enable_history_(true) {}
    
    virtual ~CalculatorBase() = default;
    
    // Pure virtual functions
    virtual T add(T a, T b) = 0;
    virtual T subtract(T a, T b) = 0;
    virtual T multiply(T a, T b) = 0;
    virtual T divide(T a, T b) = 0;
    
    // Getters
    const std::string& getName() const { return name_; }
    int getPrecision() const { return precision_; }
    const std::vector<HistoryEntry<T>>& getHistory() const { return history_; }
    
    // Utility methods
    void clearHistory() { history_.clear(); }
    void setHistoryEnabled(bool enabled) { enable_history_ = enabled; }
    
protected:
    void addToHistory(OperationType op, const std::vector<T>& operands, T result) {
        if (enable_history_) {
            history_.emplace_back(op, operands, result);
        }
    }
    
    T roundToPrecision(T value) const {
        T factor = std::pow(static_cast<T>(10), precision_);
        return std::round(value * factor) / factor;
    }
};

/**
 * Main calculator class template
 */
template<typename T = double>
class AdvancedCalculator : public CalculatorBase<T> {
private:
    using Base = CalculatorBase<T>;
    
public:
    explicit AdvancedCalculator(const std::string& name = "Advanced Calculator", int precision = 4)
        : Base(name, precision) {}
    
    // Basic arithmetic operations
    T add(T a, T b) override {
        T result = Base::roundToPrecision(a + b);
        Base::addToHistory(OperationType::ADD, {a, b}, result);
        return result;
    }
    
    T subtract(T a, T b) override {
        T result = Base::roundToPrecision(a - b);
        Base::addToHistory(OperationType::SUBTRACT, {a, b}, result);
        return result;
    }
    
    T multiply(T a, T b) override {
        T result = Base::roundToPrecision(a * b);
        Base::addToHistory(OperationType::MULTIPLY, {a, b}, result);
        return result;
    }
    
    T divide(T a, T b) override {
        if (b == T(0)) {
            throw CalculatorException("Division by zero");
        }
        T result = Base::roundToPrecision(a / b);
        Base::addToHistory(OperationType::DIVIDE, {a, b}, result);
        return result;
    }
    
    // Advanced operations
    T square(T x) {
        T result = Base::roundToPrecision(x * x);
        Base::addToHistory(OperationType::SQUARE, {x}, result);
        return result;
    }
    
    T power(T base, T exponent) {
        T result = Base::roundToPrecision(std::pow(base, exponent));
        Base::addToHistory(OperationType::POWER, {base, exponent}, result);
        return result;
    }
    
    T sqrt(T x) {
        if (x < T(0)) {
            throw CalculatorException("Cannot calculate square root of negative number");
        }
        T result = Base::roundToPrecision(std::sqrt(x));
        Base::addToHistory(OperationType::SQRT, {x}, result);
        return result;
    }
    
    T average(const std::vector<T>& numbers) {
        if (numbers.empty()) {
            throw CalculatorException("Cannot calculate average of empty vector");
        }
        T sum = std::accumulate(numbers.begin(), numbers.end(), T(0));
        T result = Base::roundToPrecision(sum / static_cast<T>(numbers.size()));
        Base::addToHistory(OperationType::AVERAGE, numbers, result);
        return result;
    }
    
    // Operator overloading for convenience
    T operator()(T a, T b, OperationType op) {
        switch (op) {
            case OperationType::ADD: return add(a, b);
            case OperationType::SUBTRACT: return subtract(a, b);
            case OperationType::MULTIPLY: return multiply(a, b);
            case OperationType::DIVIDE: return divide(a, b);
            case OperationType::POWER: return power(a, b);
            default: throw CalculatorException("Invalid binary operation");
        }
    }
    
    // Function object for statistical operations
    template<typename Func>
    T applyFunction(const std::vector<T>& numbers, Func func) {
        if (numbers.empty()) {
            throw CalculatorException("Cannot apply function to empty vector");
        }
        return func(numbers);
    }
    
    // Get history summary using lambda
    std::map<OperationType, int> getHistorySummary() const {
        std::map<OperationType, int> summary;
        std::for_each(Base::history_.begin(), Base::history_.end(),
            [&summary](const HistoryEntry<T>& entry) {
                summary[entry.getOperation()]++;
            });
        return summary;
    }
};

/**
 * Specialized calculator for integer operations
 */
class IntegerCalculator : public AdvancedCalculator<int> {
public:
    explicit IntegerCalculator(const std::string& name = "Integer Calculator")
        : AdvancedCalculator<int>(name, 0) {}
    
    int modulo(int a, int b) {
        if (b == 0) {
            throw CalculatorException("Modulo by zero");
        }
        int result = a % b;
        addToHistory(OperationType::DIVIDE, {a, b}, result); // Using DIVIDE for modulo
        return result;
    }
    
    int gcd(int a, int b) {
        a = std::abs(a);
        b = std::abs(b);
        while (b != 0) {
            int temp = b;
            b = a % b;
            a = temp;
        }
        return a;
    }
    
    int lcm(int a, int b) {
        return std::abs(a * b) / gcd(a, b);
    }
};

/**
 * Mathematical utility functions using templates and lambdas
 */
class MathUtils {
public:
    // Template function for factorial
    template<typename T>
    static T factorial(T n) {
        if (n < 0) {
            throw CalculatorException("Factorial is only defined for non-negative numbers");
        }
        return (n <= 1) ? 1 : n * factorial(n - 1);
    }
    
    // Check if number is prime
    static bool isPrime(int n) {
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
    
    // Generate fibonacci sequence using lambda
    static std::vector<int> fibonacciSequence(int length) {
        std::vector<int> sequence;
        if (length <= 0) return sequence;
        
        auto fibonacci = [&sequence](int n) -> void {
            if (n >= 1) sequence.push_back(0);
            if (n >= 2) sequence.push_back(1);
            
            for (int i = 2; i < n; ++i) {
                sequence.push_back(sequence[i-1] + sequence[i-2]);
            }
        };
        
        fibonacci(length);
        return sequence;
    }
    
    // Template function for statistical operations
    template<typename Container, typename T = typename Container::value_type>
    static T median(Container container) {
        if (container.empty()) {
            throw CalculatorException("Cannot calculate median of empty container");
        }
        
        std::sort(container.begin(), container.end());
        size_t size = container.size();
        
        if (size % 2 == 0) {
            return (container[size/2 - 1] + container[size/2]) / T(2);
        } else {
            return container[size/2];
        }
    }
};

/**
 * Calculator factory using smart pointers
 */
class CalculatorFactory {
public:
    enum class CalculatorType {
        DOUBLE_PRECISION,
        FLOAT_PRECISION,
        INTEGER_ONLY
    };
    
    template<typename T>
    static std::unique_ptr<AdvancedCalculator<T>> createCalculator(
        const std::string& name, int precision = 4) {
        return std::make_unique<AdvancedCalculator<T>>(name, precision);
    }
    
    static std::unique_ptr<IntegerCalculator> createIntegerCalculator(
        const std::string& name = "Integer Calculator") {
        return std::make_unique<IntegerCalculator>(name);
    }
};

} // namespace Calculator

/**
 * Demonstration function
 */
void demonstrateCalculator() {
    using namespace Calculator;
    
    try {
        // Create different types of calculators
        auto doubleCalc = CalculatorFactory::createCalculator<double>("Double Calculator", 4);
        auto intCalc = CalculatorFactory::createIntegerCalculator("Integer Calculator");
        
        std::cout << std::fixed << std::setprecision(4);
        
        // Double precision calculator operations
        std::cout << "=== " << doubleCalc->getName() << " ===\n";
        std::cout << "10.5 + 5.3 = " << doubleCalc->add(10.5, 5.3) << "\n";
        std::cout << "20.8 - 8.2 = " << doubleCalc->subtract(20.8, 8.2) << "\n";
        std::cout << "6.5 * 7.2 = " << doubleCalc->multiply(6.5, 7.2) << "\n";
        std::cout << "15.6 / 3.2 = " << doubleCalc->divide(15.6, 3.2) << "\n";
        std::cout << "8.5² = " << doubleCalc->square(8.5) << "\n";
        std::cout << "2^10 = " << doubleCalc->power(2.0, 10.0) << "\n";
        std::cout << "√16 = " << doubleCalc->sqrt(16.0) << "\n";
        
        std::vector<double> numbers = {1.5, 2.3, 3.7, 4.1, 5.9};
        std::cout << "Average of numbers = " << doubleCalc->average(numbers) << "\n";
        
        // Using lambda with calculator
        auto variance = doubleCalc->applyFunction(numbers, [&numbers](const std::vector<double>& nums) {
            double mean = std::accumulate(nums.begin(), nums.end(), 0.0) / nums.size();
            double variance = 0.0;
            for (double num : nums) {
                variance += (num - mean) * (num - mean);
            }
            return variance / nums.size();
        });
        std::cout << "Variance = " << variance << "\n";
        
        // Integer calculator operations
        std::cout << "\n=== " << intCalc->getName() << " ===\n";
        std::cout << "15 + 7 = " << intCalc->add(15, 7) << "\n";
        std::cout << "20 - 8 = " << intCalc->subtract(20, 8) << "\n";
        std::cout << "6 * 7 = " << intCalc->multiply(6, 7) << "\n";
        std::cout << "15 / 3 = " << intCalc->divide(15, 3) << "\n";
        std::cout << "17 % 5 = " << intCalc->modulo(17, 5) << "\n";
        std::cout << "GCD(48, 18) = " << intCalc->gcd(48, 18) << "\n";
        std::cout << "LCM(12, 8) = " << intCalc->lcm(12, 8) << "\n";
        
        // Math utilities
        std::cout << "\n=== Math Utilities ===\n";
        std::cout << "5! = " << MathUtils::factorial(5) << "\n";
        std::cout << "Is 17 prime? " << (MathUtils::isPrime(17) ? "Yes" : "No") << "\n";
        
        auto fib = MathUtils::fibonacciSequence(10);
        std::cout << "First 10 Fibonacci numbers: ";
        for (size_t i = 0; i < fib.size(); ++i) {
            if (i > 0) std::cout << ", ";
            std::cout << fib[i];
        }
        std::cout << "\n";
        
        std::vector<double> medianTest = {1.0, 3.0, 2.0, 5.0, 4.0};
        std::cout << "Median of [1,3,2,5,4] = " << MathUtils::median(medianTest) << "\n";
        
        // History summary
        std::cout << "\n=== History Summary ===\n";
        auto summary = doubleCalc->getHistorySummary();
        for (const auto& pair : summary) {
            std::cout << "Operation type " << static_cast<int>(pair.first) 
                     << ": " << pair.second << " times\n";
        }
        
    } catch (const CalculatorException& e) {
        std::cerr << e.what() << "\n";
    } catch (const std::exception& e) {
        std::cerr << "Standard exception: " << e.what() << "\n";
    }
}

/**
 * Main function
 */
int main() {
    demonstrateCalculator();
    return 0;
}