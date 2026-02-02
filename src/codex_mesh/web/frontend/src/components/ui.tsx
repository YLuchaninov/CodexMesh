import { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes } from 'react';

interface CardProps {
    title?: string;
    children: ReactNode;
    className?: string;
}

export function Card({ title, children, className = '' }: CardProps) {
    return (
        <div className={`bg-sidebar border border-border rounded-lg flex flex-col ${className}`}>
            {title && (
                <div className="p-4 border-b border-border">
                    <h3 className="font-bold text-lg">{title}</h3>
                </div>
            )}
            <div className="p-4 flex flex-col gap-3">{children}</div>
        </div>
    );
}

export function CardHeader({ children, className = '' }: { children: ReactNode; className?: string }) {
    return <div className={`p-4 border-b border-border ${className}`}>{children}</div>;
}

export function CardBody({ children, className = '' }: { children: ReactNode; className?: string }) {
    return <div className={`p-4 flex flex-col gap-3 ${className}`}>{children}</div>;
}

export function H2({ children, className = '' }: { children: ReactNode; className?: string }) {
    return <h2 className={`font-bold text-lg ${className}`}>{children}</h2>;
}

export function SubTitle({ children, className = '' }: { children: ReactNode; className?: string }) {
    return <p className={`text-xs text-slate-400 font-medium ${className}`}>{children}</p>;
}

export function Text({ children, className = '' }: { children: ReactNode; className?: string }) {
    return <p className={`text-sm text-slate-300 leading-relaxed ${className}`}>{children}</p>;
}

export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
    return (
        <button
            className={`bg-accent text-white px-4 py-2 rounded font-medium hover:bg-blue-600 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm flex items-center justify-center gap-2 ${className}`}
            {...props}
        />
    );
}

export function Input({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
    return (
        <input
            className={`bg-bg border border-border text-text placeholder:text-slate-500 px-3 py-2 rounded w-full focus:outline-none focus:ring-1 focus:ring-accent transition-all ${className}`}
            {...props}
        />
    );
}

export function Select({ className = '', ...props }: InputHTMLAttributes<HTMLSelectElement>) {
    return (
        <select
            className={`bg-bg border border-border text-text px-3 py-2 rounded focus:outline-none focus:ring-1 focus:ring-accent transition-all appearance-none cursor-pointer ${className}`}
            {...props}
        />
    );
}


export function Section({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
    return (
        <div className={`flex flex-col gap-4 ${className}`}>
            <h3 className="font-bold text-lg text-slate-100">{title}</h3>
            {children}
        </div>
    );
}

export function Spinner({ size = 16, className = '' }: { size?: number; className?: string }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`animate-spin ${className}`}
        >
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
    );
}

