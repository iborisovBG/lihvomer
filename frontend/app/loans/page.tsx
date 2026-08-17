"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import {
 Alert,
 Button,
 Card,
 CardContent,
 CardDescription,
 CardHeader,
 CardTitle,
 Skeleton,
} from "@/components/ui";
import { LoanWizard } from "@/components/loan-wizard";
import { Sheet } from "@/components/sheet";
import { SwipeActions } from "@/components/swipe-actions";
import { PartnerCard } from "@/components/partner-card";
import { LargeTitle } from "@/components/large-title";
import {
 api,
 getToken,
 type Loan,
 type LoanProjection,
} from "@/lib/api";
import { money, percent, signedNumber } from "@/lib/utils";


const INDEX_LABELS: Record<string, string> = {
 EURIBOR_3M: "Плаваща — Euribor 3 месеца",
 EURIBOR_6M: "Плаваща — Euribor 6 месеца",
 EURIBOR_12M: "Плаваща — Euribor 12 месеца",
 BLP: "Плаваща — БЛП на банката",
 FIXED: "Фиксирана лихва",
};


export default function LoansPage() {
 const router = useRouter();
 const [loans, setLoans] = useState<Loan[]>([]);
 const [projections, setProjections] = useState<LoanProjection[]>([]);
 const [editing, setEditing] = useState<Loan | null>(null);
 const [adding, setAdding] = useState(false);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);

 const load = useCallback(async () => {
 try {
 const [loanList, projectionList] = await Promise.all([
 api.loans(),
 api.projections(),
 ]);
 setLoans(loanList);
 setProjections(projectionList);
 setError(null);
 } catch (err) {
 setError((err as Error).message);
 } finally {
 setLoading(false);
 }
 }, []);

 useEffect(() => {
 if (getToken() === null) {
 router.push("/login");
 return;
 }
 load();
 }, [load, router]);

 async function remove(loan: Loan) {
 if (!window.confirm(`Да изтрия ли „${loan.label}“?`)) return;
 await api.deleteLoan(loan.id);
 load();
 }

 if (loading) return <Skeleton className="h-64 w-full" />;

 return (
 <div className="space-y-4">
 <LargeTitle
        title="Моите кредити"
        description="Всеки въведен кредит се следи автоматично и влиза в прогнозата на таблото."
        action={!adding && !editing && (
 <Button onClick={() => setAdding(true)}>
 <Plus className="h-4 w-4" />
 Добави кредит
 </Button>
 )}
      />

 {error && <Alert tone="bad">{error}</Alert>}

 <Sheet
        open={adding || editing !== null}
        onClose={() => {
          setAdding(false);
          setEditing(null);
        }}
        title={editing ? "Редакция на кредит" : "Нов кредит"}
        description={
          editing
            ? "Променете каквото се е разминало с договора."
            : "Няколко въпроса, за да сметнем вноската ви."
        }
      >
        <LoanWizard
          initial={editing}
          onSaved={() => {
            setAdding(false);
            setEditing(null);
            load();
          }}
          onCancel={() => {
            setAdding(false);
            setEditing(null);
          }}
        />
      </Sheet>

 {loans.length === 0 && !adding && (
 <Alert>
 Нямате въведени кредити. Добавете първия си кредит, за да видите как
 европейските лихви влияят на вноската ви.
 </Alert>
 )}

 <div className="grid gap-4 md:grid-cols-2">
 {loans.map((loan) => {
 const projection = projections.find((p) => p.loan_id === loan.id);
 return (
              <SwipeActions
                key={loan.id}
                actions={[
                  {
                    label: "Редакция",
                    icon: <Pencil className="h-4 w-4" aria-hidden />,
                    onClick: () => setEditing(loan),
                  },
                  {
                    label: "Изтрий",
                    icon: <Trash2 className="h-4 w-4" aria-hidden />,
                    onClick: () => remove(loan),
                    tone: "destructive",
                  },
                ]}
              >
                <Card>
 <CardHeader>
 <div className="flex items-start justify-between gap-2">
 <div>
 <CardTitle>{loan.label}</CardTitle>
 <CardDescription>
 {loan.bank_name} ·{" "}
 {loan.loan_type === "MORTGAGE"
 ? "ипотечен"
 : "потребителски"}{" "}
 · {INDEX_LABELS[loan.index_type]}
 </CardDescription>
 </div>
 <div className="hidden shrink-0 gap-1 sm:flex">
 <Button
 variant="ghost"
 size="icon"
 onClick={() => setEditing(loan)}
 aria-label="Редакция"
 >
 <Pencil className="h-4 w-4" />
 </Button>
 <Button
 variant="ghost"
 size="icon"
 onClick={() => remove(loan)}
 aria-label="Изтриване"
 >
 <Trash2 className="h-4 w-4" />
 </Button>
 </div>
 </div>
 </CardHeader>
 <CardContent>
 <dl className="grid grid-cols-2 gap-y-2 type-subhead">
 <dt className="text-muted-foreground">Оставаща главница</dt>
 <dd className="text-right font-medium tabular-nums">
 {money(loan.principal_amount, loan.currency)}
 </dd>
 <dt className="text-muted-foreground">Оставащ срок</dt>
 <dd className="text-right font-medium tabular-nums">
 {loan.remaining_months} месеца
 </dd>
 <dt className="text-muted-foreground">Текуща лихва</dt>
 <dd className="text-right font-medium tabular-nums">
 {percent(loan.current_interest_rate)}
 </dd>
 {projection && (
 <>
 <dt className="text-muted-foreground">Текуща вноска</dt>
 <dd className="text-right font-medium tabular-nums">
 {money(
 projection.current_monthly_payment,
 loan.currency,
 )}
 </dd>
 </>
 )}
 </dl>

 {projection && (
 <div className="mt-3 border-t border-border pt-3">
 <div className="mb-2 type-caption font-medium text-muted-foreground">
 Прогноза за вноската
 </div>
 <div className="grid grid-cols-4 gap-1.5 text-center">
 {projection.horizons.map((horizon) => (
 <div
 key={horizon.horizon_days}
 className="rounded-lg bg-muted p-1.5"
 >
 <div className="type-caption text-muted-foreground">
 {horizon.horizon_days}д
 </div>
 <div className="type-caption font-semibold tabular-nums">
 {horizon.projected_monthly_payment.toFixed(0)}
 </div>
 <div
 className={
 horizon.delta_monthly > 0.5
 ? "type-caption text-bad"
 : horizon.delta_monthly < -0.5
 ? "type-caption text-good"
 : "type-caption text-muted-foreground"
 }
 >
 {signedNumber(horizon.delta_monthly)}
 </div>
 </div>
 ))}
 </div>
 </div>
 )}
 </CardContent>
   </Card>

 </SwipeActions>
 );
 })}
 </div>

 {loans.length > 0 && <PartnerCard />}
 </div>
 );
}
