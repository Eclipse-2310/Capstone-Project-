# Content and Asset Gap Audit

**Date:** October 26, 2026  
**Auditor:** Valour (Release Engineering & Academic Review)  

---

## 1. Product Photography and Media Assets

### Current Status
- **Zero Image Files:** The original repository contained zero product photographs, diagrams, or icon files.
- **Strict Compliance with Visual Rules:** In accordance with project instructions, generic stock photography, AI-generated dummy visuals, and decorative icon libraries were strictly prohibited.

### Design Resolution (Typographic Presentation)
- Rather than presenting broken image placeholders or unrelated stock photos, the frontend implements an **Editorial Typographic Plate** on both the catalog grid and product detail screens.
- Each product is framed by its unique database primary key tag (`PRODUCT #<id>`), its formal inventory SKU name rendered in high-contrast editorial serif (`Bitter`), and an indexed schema badge.
- This creates an intentional, architectural aesthetic that looks designed and confident without needing external image assets.

### Schema Extensibility for Future Assets
If product photographs are captured in the future, the schema can be extended additively via a migration script:
```sql
ALTER TABLE Products ADD COLUMN image_url TEXT;
```
Until real photographs are provided, this column remains omitted to preserve clean 3NF database normalization without unused nullable fields.

---

## 2. Customer Profile and Shipping Attributes

### Current Schema Scope
- The `Customers` table stores: `Customer_id`, `Name`, `Email`, `password_hash`, `role`.

### Identified Gaps for Production Realism
- **Physical Shipping Address:** In a full commercial application, a delivery street address, city, state, and postal code are recorded. In this educational capstone, delivery is referenced to the customer's account profile.
- **Phone Number:** No contact phone column currently exists.
- **Academic Context:** These omissions are acceptable for an academic capstone demonstrating core DSA and DBMS relations, avoiding extraneous form bloat during viva demonstrations.
