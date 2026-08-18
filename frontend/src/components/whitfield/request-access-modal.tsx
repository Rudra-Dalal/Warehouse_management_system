import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button, Input } from "@/components/whitfield/primitives";
import { CheckCircle2, ShieldAlert } from "lucide-react";

export interface RequestAccessModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function RequestAccessModal({ isOpen, onClose }: RequestAccessModalProps) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [message, setMessage] = useState("");

  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState<{ fullName?: string; email?: string }>({});

  const validate = () => {
    const newErrors: { fullName?: string; email?: string } = {};

    if (!fullName.trim()) {
      newErrors.fullName = "Full name is required";
    }

    const emailTrimmed = email.trim();
    if (!emailTrimmed) {
      newErrors.email = "Work email is required";
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(emailTrimmed)) {
        newErrors.email = "Please enter a valid work email address";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) {
      return;
    }

    // Process informational request submission
    setSubmitted(true);
  };

  const handleClose = () => {
    setFullName("");
    setEmail("");
    setDepartment("");
    setMessage("");
    setErrors({});
    setSubmitted(false);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-md border-border bg-surface shadow-xl">
        {!submitted ? (
          <>
            <DialogHeader className="space-y-2 text-left">
              <DialogTitle className="text-xl font-semibold tracking-tight text-foreground">
                Request Access
              </DialogTitle>
              <DialogDescription className="text-xs leading-relaxed text-muted-foreground">
                Warehouse accounts are created by authorized administrators. Submit your details and
                contact your warehouse administrator for account activation.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="mt-4 space-y-4" noValidate>
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Full Name *
                </label>
                <Input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Alex Morgan"
                  className="mt-1"
                />
                {errors.fullName ? (
                  <p className="mt-1 text-xs text-danger">{errors.fullName}</p>
                ) : null}
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Work Email *
                </label>
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex.morgan@whitfield.com"
                  className="mt-1"
                />
                {errors.email ? <p className="mt-1 text-xs text-danger">{errors.email}</p> : null}
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Department / Team{" "}
                  <span className="normal-case text-muted-foreground/70">(Optional)</span>
                </label>
                <Input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="e.g. Reno Fulfillment Operations"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Message <span className="normal-case text-muted-foreground/70">(Optional)</span>
                </label>
                <textarea
                  rows={3}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Provide any additional context or warehouse location details..."
                  className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/70 focus:border-signal focus:outline-none"
                />
              </div>

              <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
                <ShieldAlert className="size-4 shrink-0 text-signal" />
                <span>
                  Administrators review and assign security roles (ADMIN, MANAGER, STAFF,
                  READ_ONLY).
                </span>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Submit Request
                </Button>
              </div>
            </form>
          </>
        ) : (
          <div className="space-y-4 py-2 text-center">
            <div className="mx-auto grid size-12 place-items-center rounded-full bg-ok/10 text-ok">
              <CheckCircle2 className="size-6" />
            </div>
            <div>
              <h3 className="text-lg font-semibold tracking-tight text-foreground">
                Access Request Submitted
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                Your request details have been recorded. Please contact your warehouse administrator
                for account creation and role activation.
              </p>
            </div>
            <div className="pt-2">
              <Button variant="primary" onClick={handleClose} className="w-full justify-center">
                Return to Sign In
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
