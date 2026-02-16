import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class QuickScannerTest {
    public static void main(String[] args) throws Exception {
        String source = "true false A Count_2";
        System.out.println("Input: " + source);
        System.out.println();
        
        Scanner scanner = new Scanner(new StringReader(source));
        System.out.println("Scanner created");
        
        List<Token> tokens = scanner.scanAllTokens();
        System.out.println("Total tokens: " + tokens.size());
        
        for (Token token : tokens) {
            System.out.println(token);
        }
        
        scanner.printStatistics();
    }
}
