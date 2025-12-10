# Troubleshooting Guide

## Installation Issues

### "pdflatex not found"

**Problem:** LaTeX distribution not installed or not in PATH.

**Solution:**

**macOS:**
```bash
brew install --cask mactex
# After installation, restart terminal or run:
eval "$(/usr/libexec/path_helper)"
```

**Linux:**
```bash
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-pictures
```

**Verify installation:**
```bash
which pdflatex
pdflatex --version
```

### "gs not found" or "Ghostscript error"

**Problem:** Ghostscript not installed.

**Solution:**

**macOS:**
```bash
brew install ghostscript
```

**Linux:**
```bash
sudo apt-get install ghostscript
```

**Verify installation:**
```bash
which gs
gs --version
```

### "OPENAI_API_KEY not set"

**Problem:** OpenAI API key environment variable not configured.

**Solution:**

**Temporary (current session):**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

**Permanent:**

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):
```bash
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**Or use .env file:**
```bash
cp .env.example .env
# Edit .env and add your key
```

### "Module not found" errors after installation

**Problem:** Package not installed correctly or virtual environment not activated.

**Solution:**

```bash
# Ensure you're in the project directory
cd optikz

# Reinstall with uv
uv sync

# Or with pip
source .venv/bin/activate
pip install -e .

# Verify installation
python -c "import optikz; print(optikz.__version__)"
```

## Runtime Issues

### LaTeX Compilation Errors

**Problem:** pdflatex fails to compile generated TikZ code.

**Symptoms:**
```
Error during conversion: pdflatex failed with exit code 1
```

**Diagnosis:**

Check the LaTeX log file in the run directory:
```bash
cat runs/run_*/iter_*/diagram.log
```

**Common causes:**

1. **Missing TikZ libraries:** The generated code uses libraries not included in the preamble
   - **Solution:** Add required libraries in [src/optikz/core/render.py](../src/optikz/core/render.py)

2. **Malformed TikZ syntax:** LLM generated invalid LaTeX
   - **Solution:** Increase `--iters` to allow refinement to fix it, or check iteration files to manually correct

3. **Special characters:** Unescaped special characters in labels
   - **Solution:** This usually gets fixed in refinement iterations

**Debug steps:**
```bash
# Try compiling the standalone document manually
cd runs/run_20250101_123456/
pdflatex final_standalone.tex
# Check error messages
```

### Low Similarity Scores

**Problem:** Generated TikZ doesn't visually match the original well.

**Symptoms:**
```
Step 3: similarity = 0.62
```

**Solutions:**

1. **Increase iterations:**
   ```bash
   optikz diagram.png --iters 10
   ```

2. **Lower similarity threshold:**
   ```bash
   optikz diagram.png --threshold 0.7
   ```

3. **Check HTML report** to see visual differences:
   ```bash
   optikz diagram.png --open-report
   ```

4. **Try with simpler diagrams first** to verify the pipeline works

5. **Improve input image quality:**
   - Use high-contrast images
   - Ensure text is readable
   - Avoid complex shading or photos
   - Simple geometric diagrams work best

### API Rate Limits or Errors

**Problem:** OpenAI API returns errors.

**Symptoms:**
```
Error during conversion: Rate limit exceeded
Error during conversion: Invalid API key
```

**Solutions:**

1. **Rate limits:**
   - Wait and retry
   - Use fewer iterations initially
   - Check your OpenAI usage dashboard

2. **Invalid API key:**
   ```bash
   # Verify key is correct
   echo $OPENAI_API_KEY
   # Should start with "sk-"
   ```

3. **Network errors:**
   - Check internet connectivity
   - Check if OpenAI API is down: https://status.openai.com/

### Out of Memory

**Problem:** Large images cause memory issues.

**Solutions:**

1. **Resize input images** before processing:
   ```bash
   # Using ImageMagick
   convert input.png -resize 1024x1024 resized.png
   optikz resized.png
   ```

2. **Use lower comparison resolution** in [src/optikz/core/render.py](../src/optikz/core/render.py):
   ```python
   fixed_size = (256, 256)  # Instead of (512, 512)
   ```

## Output Issues

### HTML Report Not Generated

**Problem:** Report file missing or not opening.

**Solutions:**

1. **Check if generation was skipped:**
   ```bash
   # Don't use --no-report flag
   optikz diagram.png
   ```

2. **Check run directory:**
   ```bash
   ls -la runs/run_*/report.html
   ```

3. **Manually open report:**
   ```bash
   open runs/run_*/report.html  # macOS
   xdg-open runs/run_*/report.html  # Linux
   ```

### Permission Errors

**Problem:** Cannot write to output directory.

**Solutions:**

```bash
# Use a different output directory with write permissions
optikz diagram.png --work-root ~/optikz_output

# Or fix permissions
chmod -R u+w ./runs
```

## Performance Issues

### Slow Processing

**Problem:** Processing takes too long.

**Solutions:**

1. **Reduce iterations:**
   ```bash
   optikz diagram.png --iters 2
   ```

2. **Skip report generation:**
   ```bash
   optikz diagram.png --no-report
   ```

3. **Use faster LLM model** (edit [src/optikz/core/llm.py](../src/optikz/core/llm.py)):
   ```python
   DEFAULT_MODEL = "gpt-4o-mini"  # Faster, cheaper
   ```

## Getting Help

1. **Check existing issues:** https://github.com/yourusername/optikz/issues
2. **Check the HTML report** to visualize what's happening
3. **Inspect intermediate files** in `runs/run_*/` directory
4. **Run with verbose output:**
   ```bash
   optikz diagram.png -v  # If verbose mode is implemented
   ```
5. **Create a minimal reproducible example** and open an issue

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `FileNotFoundError: pdflatex` | LaTeX not installed | Install TeX Live or MacTeX |
| `FileNotFoundError: gs` | Ghostscript not installed | Install Ghostscript |
| `Invalid API key` | Wrong or missing OpenAI key | Set OPENAI_API_KEY correctly |
| `Rate limit exceeded` | Too many API calls | Wait and retry, or upgrade plan |
| `pdflatex failed with exit code 1` | Invalid TikZ syntax | Check .log file, increase iterations |
| `Image file not found` | Wrong path to input image | Verify file path exists |
| `Similarity computation failed` | Image format issue | Ensure PNG/JPEG format |
