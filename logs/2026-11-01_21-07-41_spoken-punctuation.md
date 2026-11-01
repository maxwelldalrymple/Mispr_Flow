# Spoken punctuation and quotation marks

**Asked for:** saying "quote …" puts “ ” around it; also question mark, exclamation mark, backslash, forward slash, "etc.".

**How (`cleanup.spoken_quotes`, `cleanup.spoken_punctuation`):** applied to dictation before the cleanup model, or instead of it when cleanup is off. Terminal mode keeps its own straight quotes.

- **Quotes:**
  - "quote … end quote" / "close quote" / "unquote", and "open quote … close quote", become “…”.
  - "quote unquote fine" becomes “fine”; a lone "quote …" runs to the end of the sentence.
  - The noun is untouched: "a quote", "the quote", "quote of the day".
- **Marks:**
  - question mark, exclamation mark/point, full stop, comma, semicolon;
  - colon (only before a capital, a digit, a backslash or the end: "the colon is" stays), with "5 colon 30" → 5:30;
  - period (only at a sentence's end: "a period of time" stays);
  - ellipsis / dot dot dot; forward slash and backslash (joined: "and/or", "C:\Users");
  - parentheses, brackets, braces; hyphen, dash;
  - ampersand, at sign, hash, dollar and percent signs, asterisk, underscore;
  - new line, new paragraph.
- Whisper's own "," or "." after a spoken mark is dropped ("question mark." → "?"), but kept after brackets.

**Tests (`test_cleanup`, `test_widget`):**
- 6 quote cases plus 4 noun cases; 12 punctuation cases plus 3 ordinary-word cases.
- The post-processor applies punctuation then cleanup, or punctuation alone when cleanup is off.
- All pass.
