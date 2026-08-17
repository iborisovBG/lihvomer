import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

export function Card({
 className,
 ...props
}: React.HTMLAttributes<HTMLDivElement>) {
 return (
 <div
 className={cn(
 "glass glass-specular rounded-[1.125rem] text-card-foreground",
 className,
 )}
 {...props}
 />
 );
}

export function CardHeader({
 className,
 ...props
}: React.HTMLAttributes<HTMLDivElement>) {
 return <div className={cn("p-5 pb-2", className)} {...props} />;
}

export function CardTitle({
 className,
 ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
 return (
 <h3
 className={cn("type-headline", className)}
 {...props}
 />
 );
}

export function CardDescription({
 className,
 ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
 return (
 <p
 className={cn("mt-1 type-subhead text-muted-foreground", className)}
 {...props}
 />
 );
}

export function CardContent({
 className,
 ...props
}: React.HTMLAttributes<HTMLDivElement>) {
 return <div className={cn("p-5 pt-3", className)} {...props} />;
}

const buttonVariants = cva(
 "press inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[0.875rem] type-callout font-semibold transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-40",
 {
 variants: {
 variant: {
 default: "bg-primary text-primary-foreground hover:bg-primary/90",
 outline:
 "border border-border bg-transparent hover:bg-muted text-foreground",
 ghost: "hover:bg-muted text-foreground",
 destructive:
 "bg-destructive text-destructive-foreground hover:bg-destructive/90",
 },
 size: {
 default: "h-11 px-5", /* 44px — минималната цел за докосване */
 sm: "h-9 px-3.5 type-footnote",
 icon: "h-9 w-9",
 },
 },
 defaultVariants: { variant: "default", size: "default" },
 },
);

export interface ButtonProps
 extends React.ButtonHTMLAttributes<HTMLButtonElement>,
 VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
 ({ className, variant, size, ...props }, ref) => (
 <button
 ref={ref}
 className={cn(buttonVariants({ variant, size }), className)}
 {...props}
 />
 ),
);
Button.displayName = "Button";

export const Input = React.forwardRef<
 HTMLInputElement,
 React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
 <input
 ref={ref}
 className={cn(
 "flex h-11 w-full rounded-[0.75rem] border-0 bg-muted px-3.5 type-body",
 "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-3",
 "disabled:cursor-not-allowed disabled:opacity-50",
 className,
 )}
 {...props}
 />
));
Input.displayName = "Input";

export const Select = React.forwardRef<
 HTMLSelectElement,
 React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, ...props }, ref) => (
 <select
 ref={ref}
 className={cn(
 "flex h-11 w-full rounded-[0.75rem] border-0 bg-muted px-3.5 type-body",
 "focus-visible:outline-none",
 className,
 )}
 {...props}
 />
));
Select.displayName = "Select";

export function Label({
 className,
 ...props
}: React.LabelHTMLAttributes<HTMLLabelElement>) {
 return (
 <label
 className={cn("mb-1.5 block type-subhead font-medium text-muted-foreground", className)}
 {...props}
 />
 );
}

const badgeVariants = cva(
 "inline-flex items-center rounded-full px-2.5 py-0.5 type-caption font-semibold",
 {
 variants: {
 tone: {
 neutral: "bg-muted text-muted-foreground",
 good: "bg-[hsl(var(--good)/0.15)] text-[hsl(var(--good))]",
 warn: "bg-[hsl(var(--warn)/0.15)] text-[hsl(var(--warn))]",
 bad: "bg-[hsl(var(--bad)/0.15)] text-[hsl(var(--bad))]",
 },
 },
 defaultVariants: { tone: "neutral" },
 },
);

export function Badge({
 className,
 tone,
 ...props
}: React.HTMLAttributes<HTMLSpanElement> &
 VariantProps<typeof badgeVariants>) {
 return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export function Alert({
 className,
 tone = "neutral",
 ...props
}: React.HTMLAttributes<HTMLDivElement> & { tone?: "neutral" | "bad" }) {
 return (
 <div
 role="alert"
 className={cn(
 "rounded-[0.875rem] border p-4 type-subhead",
 tone === "bad"
 ? "border-[hsl(var(--bad)/0.3)] bg-[hsl(var(--bad)/0.1)] text-[hsl(var(--bad))]"
 : "border-transparent bg-muted text-muted-foreground",
 className,
 )}
 {...props}
 />
 );
}

export function Skeleton({
 className,
 ...props
}: React.HTMLAttributes<HTMLDivElement>) {
 return (
 <div className={cn("animate-pulse rounded-xl bg-muted", className)} {...props} />
 );
}
