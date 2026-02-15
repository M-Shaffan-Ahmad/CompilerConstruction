import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class ErrorHandler {
    public static final class LexicalError {
        private final String errorType;
        private final int line;
        private final int column;
        private final String lexeme;
        private final String reason;

        private LexicalError(String errorType, int line, int column, String lexeme, String reason) {
            this.errorType = errorType;
            this.line = line;
            this.column = column;
            this.lexeme = lexeme;
            this.reason = reason;
        }

        public String getErrorType() {
            return errorType;
        }

        public int getLine() {
            return line;
        }

        public int getColumn() {
            return column;
        }

        public String getLexeme() {
            return lexeme;
        }

        public String getReason() {
            return reason;
        }

        @Override
        public String toString() {
            return "ErrorType=" + errorType
                + ", Line=" + line
                + ", Col=" + column
                + ", Lexeme=\"" + escape(lexeme) + "\""
                + ", Reason=" + reason;
        }

        private static String escape(String value) {
            return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
        }
    }

    private final List<LexicalError> errors = new ArrayList<>();

    public void addError(String errorType, int line, int column, String lexeme, String reason) {
        errors.add(new LexicalError(errorType, line, column, lexeme, reason));
    }

    public List<LexicalError> getErrors() {
        return Collections.unmodifiableList(errors);
    }

    public boolean hasErrors() {
        return !errors.isEmpty();
    }

    public void printErrors() {
        System.out.println("Lexical Errors:");
        if (errors.isEmpty()) {
            System.out.println("  (none)");
            return;
        }
        for (LexicalError error : errors) {
            System.out.println("  " + error);
        }
    }
}
