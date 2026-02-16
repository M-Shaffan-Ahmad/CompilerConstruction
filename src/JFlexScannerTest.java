import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Test harness for JFlex Scanner implementation
 * Provides functionality to test and compare JFlex Scanner output
 */
public class JFlexScannerTest {
    
    /**
     * Scan a file and return the tokens
     */
    public static List<Token> scanFile(String filePath) throws IOException {
        String source = new String(
            Files.readAllBytes(Path.of(filePath)),
            StandardCharsets.UTF_8
        );
        
        Scanner scanner = new Scanner(new StringReader(source));
        return scanner.scanAllTokens();
    }
    
    /**
     * Scan a string directly
     */
    public static List<Token> scanString(String source) throws IOException {
        Scanner scanner = new Scanner(new StringReader(source));
        return scanner.scanAllTokens();
    }
    
    /**
     * Print tokens in a formatted manner
     */
    public static void printTokens(List<Token> tokens) {
        System.out.println("Tokens:");
        System.out.println("-".repeat(80));
        for (Token token : tokens) {
            System.out.println(token);
        }
        System.out.println("-".repeat(80));
    }
    
    /**
     * Test a single file against expected output
     */
    public static void testFile(String inputFile, String expectedFile) throws IOException {
        System.out.println("\n" + "=".repeat(80));
        System.out.println("Testing: " + inputFile);
        System.out.println("=".repeat(80));
        
        // Read and scan input
        String source = new String(
            Files.readAllBytes(Path.of(inputFile)),
            StandardCharsets.UTF_8
        );
        
        Scanner scanner = new Scanner(new StringReader(source));
        List<Token> tokens = scanner.scanAllTokens();
        
        // Print statistics
        System.out.println("\nScanning completed!");
        scanner.printStatistics();
        
        // Print tokens
        printTokens(tokens);
        
        // Print errors if any
        ErrorHandler errorHandler = scanner.getErrorHandler();
        if (errorHandler.hasErrors()) {
            System.out.println("\nErrors encountered:");
            System.out.println("-".repeat(80));
            errorHandler.printErrors();
        } else {
            System.out.println("\nNo errors found!");
        }
        
        // Print symbol table
        SymbolTable symbolTable = scanner.getSymbolTable();
        System.out.println("\nSymbol Table:");
        System.out.println("-".repeat(80));
        symbolTable.print();
        
        // Read and display expected output
        if (Files.exists(Path.of(expectedFile))) {
            System.out.println("\nExpected output:");
            System.out.println("-".repeat(80));
            String expected = new String(
                Files.readAllBytes(Path.of(expectedFile)),
                StandardCharsets.UTF_8
            );
            System.out.println(expected);
        }
    }
    
    /**
     * Run all standard tests
     */
    public static void runAllTests() throws IOException {
        String[] testFiles = {
            "tests/test1.lang",
            "tests/test2.lang",
            "tests/test3.lang",
            "tests/test4.lang",
            "tests/test5.lang"
        };
        
        String[] expectedFiles = {
            "tests/expected_test1.txt",
            "tests/expected_test2.txt",
            "tests/expected_test3.txt",
            "tests/expected_test4.txt",
            "tests/expected_test5.txt"
        };
        
        for (int i = 0; i < testFiles.length; i++) {
            try {
                testFile(testFiles[i], expectedFiles[i]);
            } catch (IOException e) {
                System.err.println("Error testing " + testFiles[i] + ": " + e.getMessage());
            }
        }
    }
    
    /**
     * Interactive mode - read from stdin and tokenize
     */
    public static void interactiveMode() throws IOException {
        System.out.println("JFlex Scanner Interactive Mode");
        System.out.println("Type your input (press EOF when done):");
        System.out.println("-".repeat(80));
        
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder input = new StringBuilder();
        String line;
        
        while ((line = reader.readLine()) != null) {
            input.append(line).append("\n");
        }
        
        String source = input.toString();
        Scanner scanner = new Scanner(new StringReader(source));
        List<Token> tokens = scanner.scanAllTokens();
        
        printTokens(tokens);
        scanner.printStatistics();
        
        if (scanner.getErrorHandler().hasErrors()) {
            System.out.println("\nErrors:");
            scanner.getErrorHandler().printErrors();
        }
    }
    
    public static void main(String[] args) throws IOException {
        if (args.length == 0) {
            // Run all tests by default
            System.out.println("JFlex Scanner Test Suite");
            System.out.println("Running all tests from tests/ directory...\n");
            runAllTests();
        } else if (args[0].equals("-i") || args[0].equals("--interactive")) {
            // Interactive mode
            interactiveMode();
        } else if (args[0].equals("-f") || args[0].equals("--file")) {
            // Test a specific file
            if (args.length < 2) {
                System.err.println("Usage: java JFlexScannerTest -f <file> [<expected_file>]");
                System.exit(1);
            }
            String expectedFile = args.length > 2 ? args[2] : null;
            testFile(args[1], expectedFile != null ? expectedFile : args[1].replace(".lang", "_expected.txt"));
        } else if (args[0].equals("-h") || args[0].equals("--help")) {
            printUsage();
        } else {
            System.err.println("Unknown option: " + args[0]);
            printUsage();
            System.exit(1);
        }
    }
    
    private static void printUsage() {
        System.out.println("Usage: java JFlexScannerTest [options]");
        System.out.println();
        System.out.println("Options:");
        System.out.println("  (no option)        Run all tests");
        System.out.println("  -i, --interactive  Interactive mode (read from stdin)");
        System.out.println("  -f, --file <file>  Test a specific file");
        System.out.println("  -h, --help         Print this help message");
        System.out.println();
        System.out.println("Examples:");
        System.out.println("  java JFlexScannerTest");
        System.out.println("  java JFlexScannerTest -i");
        System.out.println("  java JFlexScannerTest -f tests/test1.lang");
    }
}
