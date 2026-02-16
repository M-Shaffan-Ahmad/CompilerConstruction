/* JFlex Specification for Custom Language Scanner */

import java.util.*;

%%

%public
%class Scanner
%function nextToken
%type Token
%line
%column
%standalone

%{
    private SymbolTable symbolTable = new SymbolTable();
    private ErrorHandler errorHandler = new ErrorHandler();
    private Map<TokenType, Integer> tokenCounts = new EnumMap<>(TokenType.class);
    private List<Token> allTokens = new ArrayList<>();
    
    {
        initializeTokenCounts();
    }

    private void initializeTokenCounts() {
        for (TokenType tokenType : TokenType.values()) {
            tokenCounts.put(tokenType, 0);
        }
    }

    private Token createToken(TokenType type, String lexeme) {
        Token token = new Token(type, lexeme, yyline + 1, yycolumn + 1);
        tokenCounts.put(type, tokenCounts.get(type) + 1);
        
        if (type == TokenType.IDENTIFIER) {
            symbolTable.recordIdentifier(lexeme, yyline + 1, yycolumn + 1);
        }
        
        allTokens.add(token);
        return token;
    }

    private Token createErrorToken(String errorType, String lexeme, String reason) {
        errorHandler.addError(errorType, yyline + 1, yycolumn + 1, lexeme, reason);
        return null;
    }

    public List<Token> scanAllTokens() throws java.io.IOException {
        Token token;
        while ((token = nextToken()) != null) {
            // Token is already added in createToken
        }
        return Collections.unmodifiableList(allTokens);
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

    public int getTotalTokens() {
        return allTokens.size();
    }

    public void printStatistics() {
        System.out.println("Scanner Statistics:");
        System.out.println("  Total tokens: " + getTotalTokens());
        System.out.println("  Count per token type:");
        for (TokenType tokenType : TokenType.values()) {
            int count = tokenCounts.get(tokenType);
            if (count > 0) {
                System.out.println("    " + tokenType + ": " + count);
            }
        }
    }
%}

/* Regular Expressions */
WHITESPACE = [ \t\n\r]
DIGIT = [0-9]
LOWERCASE = [a-z]
UPPERCASE = [A-Z]
LETTER = [A-Za-z]
IDENTIFIER_START = {UPPERCASE}
IDENTIFIER_TAIL = [a-z0-9_]
IDENTIFIER = {UPPERCASE}{IDENTIFIER_TAIL}*

SIGN = [+\-]
INTEGER = {SIGN}?{DIGIT}+
FLOAT_BASE = {SIGN}?{DIGIT}+\.{DIGIT}+

SINGLE_LINE_COMMENT = ##[^\n]*
BOOLEAN_LITERAL = true|false
SINGLE_CHAR_OPERATOR = [+\-*/%<>=!]
PUNCTUATOR = [()\{\}\[\],;:]

%%

/* Token Rules in Priority Order */

/* 1. Single Line Comment - Priority 1 */
{SINGLE_LINE_COMMENT} {
    // Skip comments and continue to next token
    return nextToken();
}

/* 2. Boolean Literal - Priority 2 */
{BOOLEAN_LITERAL} {
    return createToken(TokenType.BOOLEAN_LITERAL, yytext());
}

/* 3. Identifier - Priority 3 */
{IDENTIFIER} {
    String text = yytext();
    if (text.length() > 31) {
        return createErrorToken("InvalidIdentifier", text, 
            "Identifier exceeds maximum length of 31 characters.");
    }
    return createToken(TokenType.IDENTIFIER, text);
}

/* 4. Floating Point Literal - Priority 4 */
{SIGN}?{DIGIT}+\.{DIGIT}+ {
    String text = yytext();
    // Extract digits after decimal point
    int dotIndex = text.lastIndexOf('.');
    int digitsAfterDot = text.length() - dotIndex - 1;
    
    if (digitsAfterDot > 6) {
        return createErrorToken("MalformedLiteral", text,
            "Floating literal exceeds maximum precision of 6 digits after decimal point.");
    }
    return createToken(TokenType.FLOATING_POINT_LITERAL, text);
}

/* 5. Integer Literal - Priority 5 */
{INTEGER} {
    return createToken(TokenType.INTEGER_LITERAL, yytext());
}

/* 6. Single Char Operator - Priority 6 */
{SINGLE_CHAR_OPERATOR} {
    return createToken(TokenType.SINGLE_CHAR_OPERATOR, yytext());
}

/* 7. Punctuator - Priority 7 */
{PUNCTUATOR} {
    return createToken(TokenType.PUNCTUATOR, yytext());
}

/* 8. Invalid Identifier (starts with lowercase) - Priority 8 */
{LOWERCASE}{IDENTIFIER_TAIL}* {
    String text = yytext();
    return createErrorToken("InvalidIdentifier", text,
        "Identifier must start with an uppercase letter.");
}

/* Whitespace - Skip */
{WHITESPACE} {
    // Skip whitespace and continue
    return nextToken();
}

/* Anything else - Invalid character */
. {
    String text = yytext();
    createErrorToken("InvalidCharacter", text,
        "Character does not start any valid token in the selected 7 token classes.");
    return nextToken();
}

<<EOF>> {
    return null;
}
