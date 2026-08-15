"use client";

import {
  ArrowDown,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Bot,
  Box,
  BrainCircuit,
  Check,
  ChevronRight,
  CircleDollarSign,
  CircleUserRound,
  Database,
  Headphones,
  Link2,
  MessageSquareText,
  PackageCheck,
  RefreshCw,
  ScanSearch,
  Send,
  ShoppingBag,
  Sparkles,
  Store,
  UsersRound,
  WandSparkles,
  X,
  Zap,
} from "lucide-react";
import { useEffect, useState, type ComponentType, type SVGProps } from "react";
import type {
  AutonomousLoopStage,
  CatalogProduct,
  CeoDecision,
  DashboardSnapshot,
  DataMode,
  IntegrationMeta,
  LinqEvent,
  SponsorName,
  TeracStudy,
} from "@/data/contracts";
import { StatusPill, type DataState } from "./status-pill";

type Icon = ComponentType<SVGProps<SVGSVGElement> & { size?: string | number }>;

type Metric = {
  label: string;
  value: string;
  note: string;
  icon: Icon;
  state: DataState;
  valueLabel?: string;
};

const stageCopy: Record<AutonomousLoopStage, { label: string; detail: string; icon: Icon }> = {
  source: { label: "Source", detail: "Scout demand", icon: ScanSearch },
  validate: { label: "Validate with humans", detail: "Terac panel", icon: UsersRound },
  list: { label: "List", detail: "Publish offer", icon: Store },
  sell: { label: "Sell", detail: "AI conversation", icon: MessageSquareText },
  fulfill: { label: "Fulfill", detail: "Route order", icon: PackageCheck },
  learn: { label: "Learn", detail: "Close the loop", icon: RefreshCw },
};

const loopStages = (Object.keys(stageCopy) as AutonomousLoopStage[]).map((id) => ({
  id,
  ...stageCopy[id],
}));

const sponsorRoles: Record<SponsorName, string> = {
  Terac: "Human feedback",
  Stripe: "Real revenue",
  Pioneer: "Verified real run",
  Linq: "AI sales",
  Band: "Agent coordination",
  Render: "Workflow execution",
  Replay: "QA verification",
  Superserve: "Sandbox execution",
  Solari: "Cloud browser audit",
};

const eventIcons: Partial<Record<LinqEvent["type"], Icon>> = {
  inbound_message: MessageSquareText,
  sales_agent: Bot,
  product_selected: Box,
  recommendation: Sparkles,
  product_page_sent: Link2,
  payment_link_sent: Link2,
  payment_completed: CircleDollarSign,
  order_fulfilled: PackageCheck,
  feedback_received: UsersRound,
};

const formatMoney = (minor: number | null | undefined, currency = "USD") => {
  if (minor === null || minor === undefined) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(minor / 100);
  } catch {
    return `${currency} ${(minor / 100).toFixed(2)}`;
  }
};

const formatTime = (timestamp: string) =>
  new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Los_Angeles",
  }).format(new Date(timestamp));

const stateForMode = (mode: DataMode): DataState => mode;

const noteForMeta = (meta: IntegrationMeta) =>
  meta.fallback === "demo" ? `${meta.label} · DEMO FALLBACK` : meta.label;

function PanelHeading({
  eyebrow,
  title,
  titleId,
  trailing,
}: {
  eyebrow: string;
  title: string;
  titleId: string;
  trailing?: React.ReactNode;
}) {
  return (
    <div className="panel-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2 id={titleId}>{title}</h2>
      </div>
      {trailing}
    </div>
  );
}

function MetricCard({ metric }: { metric: Metric }) {
  const MetricIcon = metric.icon;
  return (
    <article className={`metric metric--${metric.state}`}>
      <div className="metric__header">
        <p>{metric.label}</p>
        <MetricIcon aria-hidden="true" size={17} />
      </div>
      <strong
        aria-label={metric.valueLabel}
        className={metric.value === "Waiting" ? "metric__value metric__value--waiting" : "metric__value"}
      >
        {metric.value}
      </strong>
      <span>{metric.note}</span>
    </article>
  );
}

function AutonomousLoop({ activeStage }: { activeStage: AutonomousLoopStage | null }) {
  const activeLabel = activeStage ? stageCopy[activeStage].label : "Awaiting a live event";
  return (
    <section className="panel loop-panel" id="autonomous-loop" aria-labelledby="loop-title">
      <PanelHeading
        eyebrow="01 / Operating system"
        title="The autonomous loop"
        titleId="loop-title"
        trailing={
          <div className="loop-current" aria-label={`Current stage: ${activeLabel}`}>
            <span className="pulse-dot" aria-hidden="true" />
            {activeStage ? `CURRENTLY ${activeLabel.toUpperCase()}` : "AWAITING LIVE EVENT"}
          </div>
        }
      />
      <ol className="loop" aria-label="Autonomous commerce workflow">
        {loopStages.map((stage, index) => {
          const StageIcon = stage.icon;
          const isActive = stage.id === activeStage;
          return (
            <li
              aria-current={isActive ? "step" : undefined}
              className={isActive ? "loop-stage loop-stage--active" : "loop-stage"}
              key={stage.id}
            >
              <div className="loop-stage__node">
                <div className="loop-stage__index">0{index + 1}</div>
                <StageIcon aria-hidden="true" size={22} strokeWidth={1.8} />
                <div><strong>{stage.label}</strong><span>{stage.detail}</span></div>
              </div>
              {index < loopStages.length - 1 ? (
                <ArrowRight className="loop-stage__arrow" aria-hidden="true" size={18} />
              ) : (
                <ArrowDownRight className="loop-stage__arrow loop-stage__arrow--return" aria-hidden="true" size={18} />
              )}
            </li>
          );
        })}
      </ol>
      <div className="loop-return" aria-hidden="true">
        <span>EVERY SIGNAL BECOMES THE NEXT DECISION</span><ArrowUpRight size={15} />
      </div>
    </section>
  );
}

function DecisionCard({ decision, featured }: { decision: CeoDecision; featured: boolean }) {
  const DecisionIcon = featured ? BrainCircuit : Zap;
  return (
    <article className={featured ? "decision-card decision-card--featured" : "decision-card"}>
      <div className="decision-card__rail" aria-hidden="true"><DecisionIcon size={18} /></div>
      <div className="decision-card__body">
        <header>
          <time dateTime={decision.timestamp}>{formatTime(decision.timestamp)}</time>
          <span>{decision.agent} — {decision.title}</span>
        </header>
        <dl className="decision-details">
          <div><dt>Reason</dt><dd>{decision.reason}</dd></div>
          <div className="decision-action"><dt>Action</dt><dd><strong>{decision.action}</strong></dd></div>
          {decision.outcome ? (
            <div className="decision-outcome"><dt>Outcome</dt><dd>{decision.outcome}</dd></div>
          ) : null}
        </dl>
      </div>
    </article>
  );
}

function DecisionFeed({ snapshot }: { snapshot: DashboardSnapshot }) {
  const decisions = snapshot.decisions.data.decisions.slice(0, 3);
  const meta = snapshot.decisions.meta;
  return (
    <section className="panel decision-panel" id="decisions" aria-labelledby="decision-title">
      <PanelHeading
        eyebrow="02 / CEO agent"
        title="Decisions, not dashboards"
        titleId="decision-title"
        trailing={<StatusPill state={stateForMode(meta.mode)} label={meta.label} compact />}
      />
      <div className="decision-feed">
        {decisions.length ? decisions.map((decision, index) => (
          <DecisionCard decision={decision} featured={index === 0} key={decision.id} />
        )) : <p className="empty-state">Waiting for the first CEO decision.</p>}
      </div>
      <p className="fixture-caption">{meta.detail}</p>
    </section>
  );
}

function LinqFlow({ snapshot }: { snapshot: DashboardSnapshot }) {
  const { data, meta } = snapshot.linq;
  const outboundMilestone = data.events.some((event) => event.type === "payment_link_sent")
    ? "payment_link_sent"
    : "product_page_sent";
  const linqFlowMilestones = new Set<LinqEvent["type"]>([
    "inbound_message",
    "sales_agent",
    "product_selected",
    outboundMilestone,
  ]);
  const flow = [...data.events]
    .filter((event) => linqFlowMilestones.has(event.type))
    .sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp))
    .slice(-4);
  const connected = meta.mode === "live";
  const statusTitle = connected
    ? data.online === true ? "Sales agent online" : data.online === false ? "Sales agent offline" : "Sales agent status unavailable"
    : meta.mode === "error" ? "Linq service degraded" : "Deployment pending · webhook offline";
  const statusLabel = connected ? (data.online === true ? "ONLINE" : "OFFLINE") : meta.label;
  return (
    <section className="panel linq-panel" id="linq" aria-labelledby="linq-title">
      <PanelHeading
        eyebrow="03 / AI sales line"
        title="Linq conversation"
        titleId="linq-title"
        trailing={<StatusPill state={stateForMode(meta.mode)} label={meta.label} compact />}
      />
      <div className={connected && data.online ? "linq-status linq-status--live" : "linq-status"}>
        <div>
          <span className="linq-status__indicator" aria-hidden="true" />
          <div><strong>{statusTitle}</strong><span>{data.phoneNumber ?? "Phone number not published"}</span></div>
        </div>
        <span>{statusLabel}</span>
      </div>
      <ol className="conversation-flow" aria-label="Recent Linq inbound to decision to outbound flow">
        {flow.length ? flow.map((event, index) => {
          const FlowIcon = eventIcons[event.type] ?? Send;
          return (
            <li key={event.id}>
              <div className="conversation-flow__icon"><FlowIcon aria-hidden="true" size={16} /></div>
              <div><strong>{event.headline}</strong><span>{event.detail ?? event.direction}</span></div>
              {index < flow.length - 1 ? <ArrowDown className="conversation-flow__arrow" aria-hidden="true" size={14} /> : null}
            </li>
          );
        }) : <li><div /><div><strong>Waiting for inbound</strong><span>No Linq events yet</span></div></li>}
      </ol>
      <div className="linq-metrics" aria-label="Linq totals">
        <div><strong>{data.conversations}</strong><span>CONVERSATIONS</span></div>
        <div><strong>{data.recommendations}</strong><span>RECOMMENDATIONS</span></div>
        <div><strong>{data.paymentLinksSent}</strong><span>PAYMENT LINKS SENT</span></div>
      </div>
      <p className="fixture-caption">{meta.detail}</p>
    </section>
  );
}

function TeracProof({ study, meta }: { study?: TeracStudy; meta: IntegrationMeta }) {
  const after = study?.after.items[0];
  const before = study?.before.items.find((item) => item.id === after?.id) ?? study?.before.items[0];
  const preferred = study?.feedback.highestRatedProduct;
  const lowest = study?.feedback.lowestRatedProducts;
  const changeSummary = study?.changes.map((change) => change.description).join(" · ") || "Waiting for autonomous change";
  return (
    <section className="panel terac-panel" id="human-feedback" aria-labelledby="terac-title">
      <PanelHeading
        eyebrow="04 / Human signal → machine action"
        title="Terac changed the business"
        titleId="terac-title"
        trailing={<StatusPill state={stateForMode(meta.mode)} label={meta.label} compact />}
      />
      <div className="proof-chain">
        <article className="proof-step proof-step--before">
          <div className="proof-step__number">01</div>
          <div className="proof-step__icon"><Database aria-hidden="true" size={18} /></div>
          <p>Before human feedback</p>
          <strong>{before?.name ?? study?.before.summary ?? "Waiting for baseline"}</strong>
          <dl>
            <div><dt>Position</dt><dd>{before?.position ? `#${before.position}` : "—"}</dd></div>
            <div><dt>Price</dt><dd>{formatMoney(before?.priceMinor, before?.currency)}</dd></div>
            <div><dt>Copy</dt><dd>{before?.copy ?? "—"}</dd></div>
          </dl>
        </article>
        <ChevronRight className="proof-chain__arrow" aria-hidden="true" />
        <article className="proof-step proof-step--signal">
          <div className="proof-step__number">02</div>
          <div className="proof-step__icon"><CircleUserRound aria-hidden="true" size={18} /></div>
          <p>Terac feedback</p>
          <strong>{study ? `${study.feedback.sampleSize} human responses` : "Waiting for panel"}</strong>
          <dl>
            <div><dt>Preferred</dt><dd>{preferred ? `${preferred.name} · ${preferred.averageLikelihood}/${study?.feedback.ratingScale ?? 5}` : study?.feedback.result ?? "—"}</dd></div>
            <div><dt>Lowest</dt><dd>{lowest?.length ? lowest.map((product) => `${product.name} · ${product.averageLikelihood}/${study?.feedback.ratingScale ?? 5}`).join(" · ") : "—"}</dd></div>
            <div><dt>Overall</dt><dd>{study?.feedback.rating !== undefined ? `${study.feedback.rating}/${study.feedback.ratingScale ?? 5}` : "—"}</dd></div>
          </dl>
        </article>
        <ChevronRight className="proof-chain__arrow" aria-hidden="true" />
        <article className="proof-step proof-step--change">
          <div className="proof-step__number">03</div>
          <div className="proof-step__icon"><WandSparkles aria-hidden="true" size={18} /></div>
          <p>Autonomous change</p>
          <strong>{changeSummary}</strong>
          <dl>
            <div><dt>Agent</dt><dd>{study ? "CEO" : "—"}</dd></div>
            <div><dt>Changes</dt><dd>{study ? study.changes.length : "—"}</dd></div>
          </dl>
        </article>
        <ChevronRight className="proof-chain__arrow" aria-hidden="true" />
        <article className="proof-step proof-step--after">
          <div className="proof-step__number">04</div>
          <div className="proof-step__icon"><Sparkles aria-hidden="true" size={18} /></div>
          <p>After</p>
          <strong>{after?.name ?? study?.after.summary ?? "Waiting for updated state"}</strong>
          <dl>
            <div><dt>Position</dt><dd>{after?.position ? `#${after.position}` : "—"}</dd></div>
            <div><dt>Price</dt><dd>{formatMoney(after?.priceMinor, after?.currency)}</dd></div>
            <div>
              <dt>Status</dt>
              <dd className={after ? "positive" : undefined}>
                {after ? <Check size={12} /> : null}
                {after ? (after.active === false ? "Paused" : "Updated") : "—"}
              </dd>
            </div>
          </dl>
        </article>
      </div>
      <p className="fixture-caption">{meta.detail}</p>
    </section>
  );
}

function CatalogPanel({ products, meta }: { products: CatalogProduct[]; meta: IntegrationMeta }) {
  return (
    <section className="panel catalog-panel" id="catalog" aria-labelledby="catalog-title">
      <PanelHeading
        eyebrow="05 / Active inventory"
        title="Promoted now"
        titleId="catalog-title"
        trailing={<StatusPill state={stateForMode(meta.mode)} label={meta.label} compact />}
      />
      <div className="catalog-list">
        {products.length ? products.slice(0, 3).map((product, index) => (
          <article key={product.id}>
            <span className="catalog-list__rank">0{index + 1}</span>
            <div>
              {product.url ? (
                <a
                  href={product.url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Open Stripe checkout for ${product.name}`}
                >
                  <strong>{product.name}</strong>
                </a>
              ) : <strong>{product.name}</strong>}
              <span>{product.source} SOURCE</span>
            </div>
            <p>{formatMoney(product.priceMinor, product.currency)}</p>
            <span className={product.active ? "catalog-state catalog-state--active" : "catalog-state"}>
              {product.active ? <Check aria-hidden="true" size={11} /> : <X aria-hidden="true" size={11} />}
              {product.active ? "ACTIVE" : "PAUSED"}
            </span>
          </article>
        )) : <p className="empty-state">Waiting for catalog products.</p>}
      </div>
    </section>
  );
}

function SponsorProof({ snapshot }: { snapshot: DashboardSnapshot }) {
  return (
    <section className="sponsor-proof" aria-labelledby="sponsor-title">
      <div className="sponsor-proof__heading">
        <p className="eyebrow">Integration proof</p><h2 id="sponsor-title">Connected company stack</h2>
      </div>
      <div className="sponsor-list">
        {snapshot.sponsors.map((sponsor) => {
          const state: DataState = sponsor.status === "active" || sponsor.status === "verified"
            ? "live" : sponsor.status === "degraded" ? "error" : "pending";
          return (
            <div className={`sponsor sponsor--${state}`} key={sponsor.name} title={sponsor.detail}>
              <div><strong>{sponsor.name}</strong><span>{sponsor.summary ?? sponsorRoles[sponsor.name]}</span></div>
              <StatusPill state={state} label={sponsor.label} compact />
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function DashboardShell({ initialSnapshot }: { initialSnapshot: DashboardSnapshot }) {
  const [snapshot, setSnapshot] = useState(initialSnapshot);
  const [pollFailed, setPollFailed] = useState(false);
  const [stale, setStale] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let inFlight: AbortController | undefined;
    const poll = async () => {
      if (document.visibilityState === "hidden") return;
      inFlight?.abort();
      inFlight = new AbortController();
      try {
        const response = await fetch("/api/dashboard", { cache: "no-store", signal: inFlight.signal });
        if (!response.ok) throw new Error(`Dashboard feed returned ${response.status}`);
        const nextSnapshot = await response.json() as DashboardSnapshot;
        if (!cancelled) {
          setSnapshot(nextSnapshot);
          setPollFailed(false);
          setStale(false);
        }
      } catch (error) {
        if (!cancelled && !(error instanceof DOMException && error.name === "AbortError")) setPollFailed(true);
      }
    };
    void poll();
    const pollInterval = window.setInterval(poll, 4_000);
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void poll();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      cancelled = true;
      inFlight?.abort();
      window.clearInterval(pollInterval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  useEffect(() => {
    const updateFreshness = () => {
      setStale(Date.now() - Date.parse(snapshot.generatedAt) > 12_000);
    };
    updateFreshness();
    const freshnessInterval = window.setInterval(updateFreshness, 2_000);
    return () => window.clearInterval(freshnessInterval);
  }, [snapshot.generatedAt]);

  const isFreshLive = snapshot.isReceivingLiveData && !pollFailed && !stale;
  const headerState: DataState = pollFailed || stale ? "error" : isFreshLive ? "live" : "demo";
  const headerLabel = pollFailed ? "FEED DEGRADED" : stale ? "FEED STALE" : isFreshLive ? "LIVE" : "DEMO DATA";
  const activeStageLabel = snapshot.activeStage ? stageCopy[snapshot.activeStage].label : "Awaiting live event";
  const metrics: Metric[] = [
    {
      label: "REAL REVENUE",
      value: snapshot.metrics.revenueMinor === null ? "Waiting" : formatMoney(snapshot.metrics.revenueMinor, snapshot.metrics.revenueCurrency),
      valueLabel: snapshot.metrics.revenueMinor === null ? "Waiting for live Stripe revenue" : undefined,
      note: snapshot.metrics.revenueMinor === null ? "FOR LIVE STRIPE REVENUE" : noteForMeta(snapshot.revenue.meta),
      icon: CircleDollarSign,
      state: stateForMode(snapshot.revenue.meta.mode),
    },
    {
      label: "ORDERS",
      value: snapshot.metrics.orders === null ? "—" : String(snapshot.metrics.orders),
      note: noteForMeta(snapshot.revenue.meta),
      icon: ShoppingBag,
      state: stateForMode(snapshot.revenue.meta.mode),
    },
    {
      label: "PRODUCTS LIVE",
      value: String(snapshot.metrics.productsLive),
      note: noteForMeta(snapshot.catalog.meta),
      icon: Store,
      state: stateForMode(snapshot.catalog.meta.mode),
    },
    {
      label: "CUSTOMER CONVERSATIONS",
      value: String(snapshot.metrics.customerConversations),
      note: noteForMeta(snapshot.linq.meta),
      icon: Headphones,
      state: stateForMode(snapshot.linq.meta.mode),
    },
    {
      label: "AUTONOMOUS DECISIONS",
      value: String(snapshot.metrics.autonomousDecisions),
      note: noteForMeta(snapshot.decisions.meta),
      icon: BrainCircuit,
      state: stateForMode(snapshot.decisions.meta.mode),
    },
  ];
  const promotedProducts = snapshot.catalog.data.promotedProducts.length
    ? snapshot.catalog.data.promotedProducts : snapshot.catalog.data.products;

  return (
    <main className="dashboard-shell">
      <header className="command-header">
        <a className="brand" href="#top" aria-label="Zero Human control room home">
          <span className="brand__mark" aria-hidden="true">ZH</span>
          <span><strong>ZERO HUMAN</strong><small>CONTROL ROOM</small></span>
        </a>
        <div className="command-header__status" aria-live="polite" aria-label="Data connection status">
          <StatusPill state={headerState} label={headerLabel} />
          <span className="sync-copy">{pollFailed ? "SHOWING LAST SAFE SNAPSHOT" : `UPDATED ${formatTime(snapshot.generatedAt)}`}</span>
        </div>
      </header>
      <section className="hero" id="top" aria-labelledby="page-title">
        <div className="hero__copy">
          <div className="hero__kicker"><span className="pulse-dot" aria-hidden="true" /> AUTONOMOUS COMMERCE SYSTEM</div>
          <h1 id="page-title">AUTONOMOUS COMPANY <span>— LIVE</span></h1>
          <p>It finds demand, validates with people, sells, fulfills, and learns — without waiting for a human operator.</p>
          <div className="hero__actions">
            <a
              className="primary-button"
              href="https://storefront-omega-three.vercel.app/"
              rel="noreferrer"
              target="_blank"
            >
              OPEN LIVE STORE <ArrowUpRight aria-hidden="true" size={14} />
            </a>
          </div>
        </div>
        <div className="hero__proof" aria-label={`Current company activity: ${activeStageLabel}`}>
          <div className="hero__proof-icon"><Bot aria-hidden="true" size={24} /></div>
          <div><span>ACTIVE STAGE</span><strong>{activeStageLabel}</strong></div>
          <div className="hero__proof-motion" aria-hidden="true"><span /><span /><span /></div>
        </div>
      </section>
      <section className="metric-grid" aria-label="Company metrics">
        {metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
      </section>
      <AutonomousLoop activeStage={snapshot.activeStage} />
      <div className="dashboard-grid">
        <DecisionFeed snapshot={snapshot} />
        <LinqFlow snapshot={snapshot} />
        <TeracProof study={snapshot.terac.data.studies[0]} meta={snapshot.terac.meta} />
        <CatalogPanel products={promotedProducts} meta={snapshot.catalog.meta} />
      </div>
      <SponsorProof snapshot={snapshot} />
      <footer className="dashboard-footer">
        <p><span className="footer-dot" /> Autonomous commerce operating system</p>
        <p>Evidence updates every 4 seconds · {headerLabel}</p>
      </footer>
    </main>
  );
}
