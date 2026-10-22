import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const DialogContext = React.createContext<{
  titleId: string;
  descriptionId: string;
} | null>(null);

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

/**
 * Native <dialog> in the top layer. Focus trapping, background inertness,
 * scroll locking, Escape handling and focus restoration to the opener are
 * provided by the platform — no polyfill, no hand-rolled key handling.
 *
 * Two shapes are supported:
 *   - structured: `title` / `description` / `footer` props, children are the
 *     scrollable body;
 *   - composed: children render their own <DialogContent>, kept for the
 *     existing call-site contract.
 */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
}: DialogProps) {
  const dialogRef = React.useRef<HTMLDialogElement>(null);
  const titleId = React.useId();
  const descriptionId = React.useId();

  React.useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) {
      el.showModal();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  // Escape is native: the browser fires `cancel`, we mirror it to the parent.
  React.useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    const handleCancel = (event: Event) => {
      event.preventDefault();
      onOpenChange(false);
    };
    el.addEventListener("cancel", handleCancel);
    return () => el.removeEventListener("cancel", handleCancel);
  }, [onOpenChange]);

  const handleBackdropClick = React.useCallback(
    (event: React.MouseEvent<HTMLDialogElement>) => {
      if (event.target === dialogRef.current) {
        onOpenChange(false);
      }
    },
    [onOpenChange]
  );

  const structured =
    title !== undefined || description !== undefined || footer !== undefined;

  const contextValue = React.useMemo(
    () => ({ titleId, descriptionId }),
    [titleId, descriptionId]
  );

  return (
    <DialogContext.Provider value={contextValue}>
      <dialog
        ref={dialogRef}
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={handleBackdropClick}
        className={cn(
          "fixed inset-0 m-0 h-dvh max-h-dvh w-full max-w-full overflow-hidden border-0 bg-transparent p-0 text-foreground",
          className
        )}
      >
        <div className="flex h-full w-full items-center justify-center sm:p-6">
          {structured ? (
            <DialogPanel>
              <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-5 py-4">
                <div className="min-w-0">
                  {title ? <DialogTitle>{title}</DialogTitle> : null}
                  {description ? (
                    <DialogDescription>{description}</DialogDescription>
                  ) : null}
                </div>
                <DialogClose onClick={() => onOpenChange(false)} />
              </div>
              <div className="safe-bottom min-h-0 flex-1 overflow-y-auto px-5 py-4">
                {children}
              </div>
              {footer ? (
                <div className="shrink-0 border-t border-border px-5 py-3">
                  {footer}
                </div>
              ) : null}
            </DialogPanel>
          ) : (
            children
          )}
        </div>
      </dialog>
    </DialogContext.Provider>
  );
}

/**
 * The visible surface. Mobile: a full-screen sheet. Desktop: a centred panel
 * with a hairline border and the modal shadow.
 */
const DialogPanel = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative flex h-full w-full max-w-none flex-col overflow-hidden rounded-none bg-card text-card-foreground",
      "sm:h-auto sm:max-h-[calc(100dvh-3rem)] sm:max-w-[560px] sm:rounded-xl sm:border sm:border-border sm:shadow-modal",
      className
    )}
    {...props}
  />
));
DialogPanel.displayName = "DialogPanel";

export function DialogContent({
  className,
  children,
  onClose,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { onClose?: () => void }) {
  return (
    <DialogPanel className={className} {...props}>
      {onClose ? (
        <div className="absolute right-2 top-2 z-10">
          <DialogClose onClick={onClose} />
        </div>
      ) : null}
      {children}
    </DialogPanel>
  );
}
DialogContent.displayName = "DialogContent";

export function DialogHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1", className)} {...props} />;
}
DialogHeader.displayName = "DialogHeader";

export function DialogTitle({
  className,
  id,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement> & { id?: string }) {
  const context = React.useContext(DialogContext);
  return (
    <h2
      id={id ?? context?.titleId}
      className={cn("text-headline text-foreground", className)}
      {...props}
    />
  );
}
DialogTitle.displayName = "DialogTitle";

export function DialogDescription({
  className,
  id,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement> & { id?: string }) {
  const context = React.useContext(DialogContext);
  return (
    <p
      id={id ?? context?.descriptionId}
      className={cn("text-body-sm text-muted-foreground", className)}
      {...props}
    />
  );
}
DialogDescription.displayName = "DialogDescription";

function DialogClose({
  onClick,
  className,
}: {
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Cerrar"
      className={cn(
        "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors duration-fast ease-out hover:bg-muted hover:text-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "pointer-fine:h-10 pointer-fine:w-10",
        className
      )}
    >
      <X className="h-5 w-5" aria-hidden="true" />
    </button>
  );
}
