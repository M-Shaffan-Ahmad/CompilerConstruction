import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class ManualScanner {
    private static final int PRIORITY_SINGLE_LINE_COMMENT = 1;
    private static final int PRIORITY_BOOLEAN_LITERAL = 2;
    private static final int PRIORITY_IDENTIFIER = 3;
    private static final int PRIORITY_FLOATING_POINT_LITERAL = 4;
    private static final int PRIORITY_INTEGER_LITERAL = 5;
    private static final int PRIORITY_SINGLE_CHAR_OPERATOR = 6;
    private static final int PRIORITY_PUNCTUATOR = 7;
    private static final int PRIORITY_INVALID_IDENTIFIER = 8;

    private static final Set<Character> PUNCTUATORS;
    private static final Set<Character> SINGLE_CHAR_OPERATORS;

    static {
        Set<Character> punctuators = new HashSet<>(Arrays.asList(
            '(', ')', '{', '}', '[', ']', ',', ';', ':'
        ));
        PUNCTUATORS = Collections.unmodifiableSet(punctuators);

        Set<Character> singleCharOperators = new HashSet<>(Arrays.asList(
            '+', '-', '*', '/', '%', '<', '>', '=', '!'
        ));
        SINGLE_CHAR_OPERATORS = Collections.unmodifiableSet(singleCharOperators);
    }

    private final String source;
    private final List<Token> tokens = new ArrayList<>();
    private final EnumMap<TokenType, Integer> tokenCounts = new EnumMap<>(TokenType.class);
    private final SymbolTable symbolTable = new SymbolTable();
    private final ErrorHandler errorHandler = new ErrorHandler();

    private int index = 0;
    private int line = 1;
    private int column = 1;
    private final int linesProcessed;

    public ManualScanner(String source) {
        this.source = source == null ? "" : source;
        this.linesProcessed = computeLineCount(this.source);
        for (TokenType tokenType : TokenType.values()) {
            tokenCounts.put(tokenType, 0);
        }
    }

    public List<Token> scanTokens() {
        while (!isAtEnd()) {
            if (isWhitespace(peek())) {
                consumeWhitespace();
                continue;
            }

            int startLine = line;
            int startColumn = column;
            MatchResult best = chooseBestMatch();

            if (best == null) {
                String lexeme = String.valueOf(peek());
                errorHandler.addError(
                    "InvalidCharacter",
                    startLine,
                    startColumn,
                    lexeme,
                    "Character does not start any valid token in the selected 7 token classes."
                );
                consume(1);
                continue;
            }

            if (best.length <= 0) {
                errorHandler.addError(
                    "InternalScannerError",
                    startLine,
                    startColumn,
                    "",
                    "Zero-length match produced by scanner."
                );
                consume(1);
                continue;
            }

            String lexeme = source.substring(index, Math.min(index + best.length, source.length()));
            consume(best.length);

            if (best.errorType != null) {
                errorHandler.addError(best.errorType, startLine, startColumn, lexeme, best.errorReason);
                continue;
            }

            //comment out for not skipping single line comment
            if (best.type == TokenType.SINGLE_LINE_COMMENT) {
                continue;
            }

            Token token = new Token(best.type, lexeme, startLine, startColumn);
            tokens.add(token);
            tokenCounts.put(best.type, tokenCounts.get(best.type) + 1);

            if (best.type == TokenType.IDENTIFIER) {
                symbolTable.recordIdentifier(lexeme, startLine, startColumn);
            }
        }
        return Collections.unmodifiableList(tokens);
    }

    public SymbolTable getSymbolTable() {
        return symbolTable;
    }

    public ErrorHandler getErrorHandler() {
        return errorHandler;
    }

    public Map<TokenType, Integer> getTokenCounts() {
        return Collections.unmodifiableMap(tokenCounts);
    }

    public int getLinesProcessed() {
        return linesProcessed;
    }

    public int getTotalTokens() {
        return tokens.size();
    }

    public void printStatistics() {
        System.out.println("Scanner Statistics:");
        System.out.println("  Total tokens: " + getTotalTokens());
        System.out.println("  Lines processed: " + linesProcessed);
        System.out.println("  Count per token type:");
        for (TokenType tokenType : TokenType.values()) {
            int count = tokenCounts.get(tokenType);
            if (count > 0) {
                System.out.println("    " + tokenType + ": " + count);
            }
        }
    }

    private MatchResult chooseBestMatch() {
        List<MatchResult> candidates = new ArrayList<>(8);
        addCandidate(candidates, matchSingleLineComment());
        addCandidate(candidates, matchBooleanLiteral());
        addCandidate(candidates, matchIdentifier());
        addCandidate(candidates, matchFloatingPointLiteral());
        addCandidate(candidates, matchIntegerLiteral());
        addCandidate(candidates, matchSingleCharOperator());
        addCandidate(candidates, matchPunctuator());
        addCandidate(candidates, matchInvalidLowercaseIdentifier());

        if (candidates.isEmpty()) {
            return null;
        }

        MatchResult best = candidates.get(0);
        for (int i = 1; i < candidates.size(); i++) {
            MatchResult current = candidates.get(i);
            if (current.length > best.length) {
                best = current;
                continue;
            }
            if (current.length == best.length && current.priority < best.priority) {
                best = current;
            }
        }
        return best;
    }

    private static void addCandidate(List<MatchResult> candidates, MatchResult candidate) {
        if (candidate != null) {
            candidates.add(candidate);
        }
    }

    private MatchResult matchSingleLineComment() {
        if (!startsWith("##")) {
            return null;
        }
        int i = index + 2;
        while (i < source.length() && source.charAt(i) != '\n') {
            i++;
        }
        return MatchResult.token(i - index, TokenType.SINGLE_LINE_COMMENT, PRIORITY_SINGLE_LINE_COMMENT);
    }

    private MatchResult matchBooleanLiteral() {
        if (startsWith("false") && isWordBoundary(index + 5)) {
            return MatchResult.token(5, TokenType.BOOLEAN_LITERAL, PRIORITY_BOOLEAN_LITERAL);
        }
        if (startsWith("true") && isWordBoundary(index + 4)) {
            return MatchResult.token(4, TokenType.BOOLEAN_LITERAL, PRIORITY_BOOLEAN_LITERAL);
        }
        return null;
    }

    private MatchResult matchIdentifier() {
        if (!isUpperAscii(peek())) {
            return null;
        }

        int i = index + 1;
        while (i < source.length() && isIdentifierLikeChar(source.charAt(i))) {
            i++;
        }

        int length = i - index;
        if (length > 31) {
            return MatchResult.error(
                length,
                PRIORITY_IDENTIFIER,
                "InvalidIdentifier",
                "Identifier exceeds maximum length of 31 characters."
            );
        }

        for (int j = index + 1; j < i; j++) {
            if (!isIdentifierTail(source.charAt(j))) {
                return MatchResult.error(
                    length,
                    PRIORITY_IDENTIFIER,
                    "InvalidIdentifier",
                    "Identifier tail allows only lowercase letters, digits, or underscore."
                );
            }
        }

        return MatchResult.token(length, TokenType.IDENTIFIER, PRIORITY_IDENTIFIER);
    }

    private MatchResult matchFloatingPointLiteral() {
        int i = index;
        boolean hasSign = false;
        if (i < source.length() && (source.charAt(i) == '+' || source.charAt(i) == '-')) {
            hasSign = true;
            i++;
        }

        int digitsBeforeDot = 0;
        while (i < source.length() && isDigitAscii(source.charAt(i))) {
            i++;
            digitsBeforeDot++;
        }

        if (digitsBeforeDot == 0) {
            if (
                hasSign
                    && i < source.length()
                    && source.charAt(i) == '.'
                    && i + 1 < source.length()
                    && isDigitAscii(source.charAt(i + 1))
            ) {
                int malformedEnd = consumeMalformedNumericSequence();
                return MatchResult.error(
                    malformedEnd - index,
                    PRIORITY_FLOATING_POINT_LITERAL,
                    "MalformedLiteral",
                    "Floating literal must contain digits before decimal point."
                );
            }
            return null;
        }

        if (i >= source.length() || source.charAt(i) != '.') {
            return null;
        }
        i++;

        int digitsAfterDot = 0;
        while (i < source.length() && isDigitAscii(source.charAt(i))) {
            i++;
            digitsAfterDot++;
        }

        if (digitsAfterDot == 0) {
            int malformedEnd = consumeMalformedNumericSequence();
            return MatchResult.error(
                malformedEnd - index,
                PRIORITY_FLOATING_POINT_LITERAL,
                "MalformedLiteral",
                "Floating literal requires at least one digit after decimal point."
            );
        }

        if (digitsAfterDot > 6) {
            int malformedEnd = consumeMalformedNumericSequence();
            return MatchResult.error(
                malformedEnd - index,
                PRIORITY_FLOATING_POINT_LITERAL,
                "MalformedLiteral",
                "Floating literal allows at most 6 digits after decimal point."
            );
        }

        if (i < source.length() && source.charAt(i) == '.') {
            int malformedEnd = consumeMalformedNumericSequence();
            return MatchResult.error(
                malformedEnd - index,
                PRIORITY_FLOATING_POINT_LITERAL,
                "MalformedLiteral",
                "Floating literal contains multiple decimal points."
            );
        }

        if (i < source.length() && (source.charAt(i) == 'e' || source.charAt(i) == 'E')) {
            int exp = i + 1;
            if (exp < source.length() && (source.charAt(exp) == '+' || source.charAt(exp) == '-')) {
                exp++;
            }

            int exponentDigits = 0;
            while (exp < source.length() && isDigitAscii(source.charAt(exp))) {
                exp++;
                exponentDigits++;
            }

            if (exponentDigits == 0) {
                int malformedEnd = consumeMalformedNumericSequence();
                return MatchResult.error(
                    malformedEnd - index,
                    PRIORITY_FLOATING_POINT_LITERAL,
                    "MalformedLiteral",
                    "Exponent part must contain at least one digit."
                );
            }

            i = exp;
        }

        return MatchResult.token(i - index, TokenType.FLOATING_POINT_LITERAL, PRIORITY_FLOATING_POINT_LITERAL);
    }

    private MatchResult matchIntegerLiteral() {
        int i = index;
        if (i < source.length() && (source.charAt(i) == '+' || source.charAt(i) == '-')) {
            i++;
        }

        int digits = 0;
        while (i < source.length() && isDigitAscii(source.charAt(i))) {
            i++;
            digits++;
        }

        if (digits == 0) {
            return null;
        }

        return MatchResult.token(i - index, TokenType.INTEGER_LITERAL, PRIORITY_INTEGER_LITERAL);
    }

    private MatchResult matchSingleCharOperator() {
        if (SINGLE_CHAR_OPERATORS.contains(peek())) {
            return MatchResult.token(1, TokenType.SINGLE_CHAR_OPERATOR, PRIORITY_SINGLE_CHAR_OPERATOR);
        }
        return null;
    }

    private MatchResult matchPunctuator() {
        if (PUNCTUATORS.contains(peek())) {
            return MatchResult.token(1, TokenType.PUNCTUATOR, PRIORITY_PUNCTUATOR);
        }
        return null;
    }

    private MatchResult matchInvalidLowercaseIdentifier() {
        if (!isLowerAscii(peek())) {
            return null;
        }

        int i = index;
        while (i < source.length() && isIdentifierLikeChar(source.charAt(i))) {
            i++;
        }

        String candidate = source.substring(index, i);
        if ("true".equals(candidate) || "false".equals(candidate)) {
            return null;
        }

        return MatchResult.error(
            i - index,
            PRIORITY_INVALID_IDENTIFIER,
            "InvalidIdentifier",
            "Identifier must start with an uppercase letter."
        );
    }

    private int consumeMalformedNumericSequence() {
        int i = index;
        if (i < source.length() && (source.charAt(i) == '+' || source.charAt(i) == '-')) {
            i++;
        }

        while (i < source.length()) {
            char c = source.charAt(i);
            if (
                isDigitAscii(c)
                    || isLowerAscii(c)
                    || isUpperAscii(c)
                    || c == '.'
                    || c == '+'
                    || c == '-'
            ) {
                i++;
                continue;
            }
            break;
        }

        return Math.max(i, index + 1);
    }

    private void consumeWhitespace() {
        while (!isAtEnd() && isWhitespace(peek())) {
            consume(1);
        }
    }

    private void consume(int length) {
        for (int consumed = 0; consumed < length && !isAtEnd(); consumed++) {
            char c = source.charAt(index);
            index++;
            if (c == '\n') {
                line++;
                column = 1;
            } else {
                column++;
            }
        }
    }

    private boolean isAtEnd() {
        return index >= source.length();
    }

    private boolean startsWith(String text) {
        return source.startsWith(text, index);
    }

    private char peek() {
        return source.charAt(index);
    }

    private boolean isWordBoundary(int position) {
        if (position >= source.length()) {
            return true;
        }
        return !isIdentifierLikeChar(source.charAt(position));
    }

    private static boolean isIdentifierTail(char c) {
        return isLowerAscii(c) || isDigitAscii(c) || c == '_';
    }

    private static boolean isIdentifierLikeChar(char c) {
        return isLowerAscii(c) || isUpperAscii(c) || isDigitAscii(c) || c == '_';
    }

    private static boolean isWhitespace(char c) {
        return c == ' ' || c == '\t' || c == '\r' || c == '\n';
    }

    private static boolean isLowerAscii(char c) {
        return c >= 'a' && c <= 'z';
    }

    private static boolean isUpperAscii(char c) {
        return c >= 'A' && c <= 'Z';
    }

    private static boolean isDigitAscii(char c) {
        return c >= '0' && c <= '9';
    }

    private static int computeLineCount(String text) {
        if (text.isEmpty()) {
            return 0;
        }

        int count = 1;
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) == '\n') {
                count++;
            }
        }
        if (text.charAt(text.length() - 1) == '\n') {
            count--;
        }
        return Math.max(count, 1);
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 1) {
            System.out.println("Usage: java ManualScanner <source-file>");
            return;
        }

        Path sourceFile = Path.of(args[0]);
        String program = Files.readString(sourceFile, StandardCharsets.UTF_8);

        ManualScanner scanner = new ManualScanner(program);
        List<Token> tokens = scanner.scanTokens();

        for (Token token : tokens) {
            System.out.println(token);
        }
        System.out.println();

        scanner.printStatistics();
        System.out.println();
        scanner.getSymbolTable().print();
        System.out.println();
        scanner.getErrorHandler().printErrors();
    }

    private static final class MatchResult {
        private final int length;
        private final int priority;
        private final TokenType type;
        private final String errorType;
        private final String errorReason;

        private MatchResult(int length, int priority, TokenType type, String errorType, String errorReason) {
            this.length = length;
            this.priority = priority;
            this.type = type;
            this.errorType = errorType;
            this.errorReason = errorReason;
        }

        private static MatchResult token(int length, TokenType type, int priority) {
            return new MatchResult(length, priority, type, null, null);
        }

        private static MatchResult error(int length, int priority, String errorType, String errorReason) {
            return new MatchResult(length, priority, null, errorType, errorReason);
        }
    }
}
