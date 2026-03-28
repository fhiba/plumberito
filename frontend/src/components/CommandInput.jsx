import { useState, useEffect, useRef } from "react";

const ANIM_DURATION = 180;

export default function CommandInput({ onSubmit, disabled }) {
  const [value, setValue] = useState("");
  const [buttonMounted, setButtonMounted] = useState(false);
  const [buttonExiting, setButtonExiting] = useState(false);
  const exitTimer = useRef(null);

  const hasText = value.trim().length > 0;

  useEffect(() => {
    clearTimeout(exitTimer.current);
    if (hasText) {
      setButtonExiting(false);
      setButtonMounted(true);
    } else if (buttonMounted) {
      setButtonExiting(true);
      exitTimer.current = setTimeout(() => {
        setButtonMounted(false);
        setButtonExiting(false);
      }, ANIM_DURATION);
    }
  }, [hasText]);

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      handleSubmit(e);
    }
  }

  return (
    <div
      className="w-full border-t-4 border-[#1e1b13] p-6 bg-surface-container-low"
      style={{ backgroundImage: "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(30, 27, 19, 0.02) 10px, rgba(30, 27, 19, 0.02) 20px)" }}
    >
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex flex-col gap-2">
        <label className="text-[10px] font-black uppercase tracking-[0.3em] text-[#1e1b13] flex items-center gap-2 font-label">
          <span className="material-symbols-outlined text-xs">keyboard</span>
          COMMAND_INPUT_PROMPT
        </label>
        <div className="flex gap-3 items-stretch">
          <textarea
            className="flex-grow bg-surface border-2 border-[#1e1b13] px-4 py-3 font-mono text-sm placeholder:opacity-30 focus:outline-none focus:border-primary-container resize-none transition-none brutalist-shadow"
            style={buttonExiting ? { animation: `textareaRebound ${ANIM_DURATION}ms cubic-bezier(0.22, 1, 0.36, 1) both` } : undefined}
            placeholder="TYPE_COMMAND_HERE..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={disabled}
          />
          {buttonMounted && (
            <button
              type="submit"
              style={{ animation: `${buttonExiting ? "stampOut" : "stampIn"} ${ANIM_DURATION}ms cubic-bezier(0.22, 1, 0.36, 1) both` }}
              className="bg-primary-container text-white border-2 border-[#1e1b13] px-8 font-headline font-black uppercase tracking-widest text-sm brutalist-shadow hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-none active:bg-primary"
            >
              EXECUTE
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
