---
title: "E-invoice for RCM self-invoices: RCMDOM and RCMIMP explained"
date: '2026-10-23'
service: gst-returns
author: CA. Kunal Darwani
summary: GSTN has added RCMDOM and RCMIMP supply types so businesses can generate IRNs for reverse charge self-invoices. What changes, who is covered and how to prepare.
meta_description: "GSTN's RCMDOM and RCMIMP supply types let recipients generate IRNs for RCM self-invoices. Now in sandbox; go-live date awaited. Who is covered, next steps."
keywords: ["e-invoice for RCM self-invoice", "RCMDOM RCMIMP e-invoice", "self-invoice reverse charge e-invoicing", "IRN for import of services self-invoice", "GSTN advisory 16 October 2026"]
faq:
  - q: "Is e-invoicing of RCM self-invoices mandatory from today?"
    a: "No. As on 23 October 2026 the RCMDOM and RCMIMP facility is available only in the sandbox of the six IRPs. GSTN has said the production rollout date and the start of the reporting requirement will be communicated later, subject to notifications."
  - q: "Do small businesses below ₹5 crore turnover need to e-invoice self-invoices?"
    a: "The GSTN advisory says the facility is intended for taxpayers with aggregate annual turnover of ₹5 crore and above, which is the present e-invoicing threshold. Others continue to issue self-invoices under Rule 46 and Rule 47A without an IRN."
  - q: "Is an e-way bill generated with an RCMDOM or RCMIMP e-invoice?"
    a: "The advisory does not link these supply types to e-way bills. RCMIMP covers only import of services. For goods moved under an RCMDOM self-invoice, existing e-way bill rules continue to apply."
  - q: "Will the self-invoice still need to be issued within 30 days?"
    a: "Yes. Rule 47A requires a recipient liable under section 9(3) or 9(4) to issue the self-invoice within 30 days of receiving the supply. The new e-invoice facility only changes how that invoice is reported."
ai_drafted: true
---
GST e-invoicing is being extended to self-invoices that a registered recipient issues under the reverse charge mechanism (RCM). Through an advisory dated 16 October 2026, GSTN introduced two new supply types – **RCMDOM** for specified domestic supplies received from unregistered persons and **RCMIMP** for import of services – so that recipients with aggregate annual turnover of ₹5 crore and above can generate an Invoice Reference Number (IRN) for such self-invoices. The facility is presently in sandbox only; the production date will be announced later.

## What did GSTN announce on 16 October 2026?

The GST Council, in its 57th meeting held on 8 October 2026, recommended extending e-invoicing to two kinds of inward supplies on which the recipient pays tax under RCM:

- domestic supplies received from an unregistered person, and
- import of services.

Following that recommendation, GSTN added two supply types to the existing e-invoice schema:

| Supply type | Covers | Who reports it |
|---|---|---|
| RCMDOM | Self-invoices for specified domestic supplies received from unregistered persons, where the registered recipient pays tax under RCM | Registered recipient |
| RCMIMP | Self-invoices for import of services from suppliers located outside India, where the registered recipient pays tax under RCM | Registered recipient |

Under the existing B2B framework, an e-invoice is ordinarily reported by the supplier. Under these two supply types, the recipient reports its own self-invoice to an Invoice Registration Portal (IRP), selects RCMDOM or RCMIMP, and receives an IRN once the details pass validation.

## Is it mandatory to e-invoice RCM self-invoices now?

Not yet. The position as on the date of this article is:

| Point | Status |
|---|---|
| System changes | Done in the sandbox of all six authorised IRPs |
| Production rollout | Date to be communicated by GSTN |
| Legal requirement | Subject to notifications to be issued by the Government |
| Technical specifications | To be issued by NIC IRP-1 in a release note |
| Webinar | GSTN and IRPs to hold one; details awaited |

Until the notification and production date are announced, self-invoices continue to be issued in the existing manner. The advisory, however, asks taxpayers and their software providers to complete development and testing now, so that the change does not disrupt monthly compliance when it goes live.

## Who will be covered?

The advisory states that the facility is intended for registered taxpayers with aggregate annual turnover (AATO) of ₹5 crore and above – the current eligibility threshold for e-invoicing. In practice, this means the businesses already generating IRNs on their outward B2B invoices are the ones that will also need to report RCM self-invoices. The final scope and effective date will depend on the notification.

Taxpayers below the e-invoicing threshold are not covered by the advisory. They continue to issue self-invoices in the usual format without an IRN.

## When does a business issue a self-invoice under RCM?

Section 31(3)(f) of the CGST Act requires a registered person who is liable to pay tax under reverse charge to issue an invoice for goods or services received from a supplier who is not registered. Common situations include:

- **Import of services** – for example, software subscriptions, consultancy or marketing services billed by an overseas supplier. The foreign supplier is not registered in India, so the Indian recipient pays IGST under RCM and issues the self-invoice.
- **Notified supplies from unregistered persons** – supplies notified under section 9(3), such as legal services by an advocate, or classes notified under section 9(4), where the supplier is not registered.

Under section 31(3)(g), the recipient also issues a payment voucher when paying such a supplier.

## What is the time limit for the self-invoice?

Rule 47A of the CGST Rules, inserted by Notification No. 20/2024-Central Tax dated 8 October 2024, sets the time limit:

| Requirement | Time limit |
|---|---|
| Self-invoice by a recipient liable under section 9(3) or 9(4) | Within 30 days from the date of receipt of the supply |

For outward e-invoices, Rule 48(5) provides that an invoice not issued in the manner required by Rule 48(4) is not treated as an invoice. If the coming notification brings RCM self-invoices within the e-invoice requirement, the same discipline is likely to matter for them. Businesses should therefore track the date of receipt of each RCM supply carefully, as delays can affect interest and the input tax credit position.

## How should businesses prepare?

1. **List RCM inward supplies.** Review the purchase ledger for the last twelve months and identify payments to unregistered suppliers and overseas service providers on which tax is paid under RCM.
2. **Separate domestic and import cases.** Map each case to RCMDOM or RCMIMP. RCMIMP is limited to services; import of goods continues under customs.
3. **Check the ERP or billing software.** Confirm with the GSP, ASP or ERP vendor that self-invoice generation, the new supply types and IRN storage are being built and tested in the sandbox.
4. **Fix internal timelines.** Record the date of receipt of the supply, the self-invoice date and the payment date separately, so the 30-day limit in Rule 47A is met.
5. **Reconcile with returns.** RCM liability and the related credit continue to flow through GSTR-3B. Make sure the self-invoices match the RCM liability reported each month.

For the basics of the existing e-invoicing threshold and the 30-day reporting rule for outward invoices, see [GST e-invoicing applicability: ₹5 crore limit and 30-day rule](gst-e-invoicing-applicability-5-crore-30-day-rule.html). Monthly reporting of RCM liability is part of routine [GST return filing](../services/gst-returns.html).

## What should businesses watch for next?

Three announcements will decide the actual compliance date: the Government notification extending e-invoicing to these self-invoices, the NIC release note with technical validations, and GSTN's production rollout date. Until then, the change is a readiness exercise rather than a filing obligation.

*The information in this article reflects the law as on the date of publication and is for general guidance only.*

**CA. Kunal Darwani**
