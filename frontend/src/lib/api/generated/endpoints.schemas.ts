export const ActionTypeEnum = {
  outreach: 'outreach',
  legal_filing: 'legal_filing',
  media: 'media',
  advocacy: 'advocacy',
  investigation: 'investigation',
  other: 'other',
} as const;

export const BlankEnum = {
  '': '',
} as const;

export const CurrentStatusEnum = {
  detained: 'detained',
  disappeared: 'disappeared',
  restricted_movement: 'restricted_movement',
  released: 'released',
  deceased: 'deceased',
  unknown: 'unknown',
  stateless: 'stateless',
  rights_restricted: 'rights_restricted',
} as const;

export const GenderEnum = {
  M: 'M',
  F: 'F',
  O: 'O',
  U: 'U',
} as const;

export const KindEnum = {
  record_created: 'record_created',
  record_updated: 'record_updated',
  status_done: 'status_done',
  record_seen: 'record_seen',
} as const;

export const MediaTypeEnum = {
  photo: 'photo',
  document: 'document',
  video: 'video',
  link: 'link',
} as const;

export const MedicalStatusEnum = {
  unknown: 'unknown',
  healthy: 'healthy',
  health_concerns: 'health_concerns',
  critical: 'critical',
  deceased: 'deceased',
} as const;

export const NullEnum = {
} as const;

export const QualityTierEnum = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const RelationshipTypeEnum = {
  parent: 'parent',
  child: 'child',
  sibling: 'sibling',
  spouse: 'spouse',
  other: 'other',
} as const;

export const RoleEnum = {
  family: 'family',
  advocate: 'advocate',
  lawyer: 'lawyer',
  official: 'official',
  journalist: 'journalist',
  reporter: 'reporter',
  other: 'other',
} as const;

export const SourceTypeEnum = {
  firsthand: 'firsthand',
  secondhand: 'secondhand',
  news: 'news',
  document: 'document',
} as const;

export const StatusEnum = {
  open: 'open',
  in_progress: 'in_progress',
  done: 'done',
} as const;

export const VisibilityEnum = {
  public: 'public',
  restricted: 'restricted',
  sensitive: 'sensitive',
} as const;

export const CaseworkListActionType = {
  advocacy: 'advocacy',
  investigation: 'investigation',
  legal_filing: 'legal_filing',
  media: 'media',
  other: 'other',
  outreach: 'outreach',
} as const;

export const CaseworkListStatus = {
  done: 'done',
  in_progress: 'in_progress',
  open: 'open',
} as const;

export const ContactsListRole = {
  advocate: 'advocate',
  family: 'family',
  journalist: 'journalist',
  lawyer: 'lawyer',
  official: 'official',
  other: 'other',
  reporter: 'reporter',
} as const;

export const MediaListMediaType = {
  document: 'document',
  link: 'link',
  photo: 'photo',
  video: 'video',
} as const;

export const MediaListVisibility = {
  public: 'public',
  restricted: 'restricted',
  sensitive: 'sensitive',
} as const;

export const NotificationsListKind = {
  record_created: 'record_created',
  record_seen: 'record_seen',
  record_updated: 'record_updated',
  status_done: 'status_done',
} as const;

export const PersonsListCurrentStatus = {
  deceased: 'deceased',
  detained: 'detained',
  disappeared: 'disappeared',
  released: 'released',
  restricted_movement: 'restricted_movement',
  rights_restricted: 'rights_restricted',
  stateless: 'stateless',
  unknown: 'unknown',
} as const;

export const PersonsListGender = {
  F: 'F',
  M: 'M',
  O: 'O',
  U: 'U',
} as const;

export const PersonsListMedicalStatus = {
  critical: 'critical',
  deceased: 'deceased',
  health_concerns: 'health_concerns',
  healthy: 'healthy',
  unknown: 'unknown',
} as const;

export const PersonsListQualityTier = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const PersonsCountriesListCurrentStatus = {
  deceased: 'deceased',
  detained: 'detained',
  disappeared: 'disappeared',
  released: 'released',
  restricted_movement: 'restricted_movement',
  rights_restricted: 'rights_restricted',
  stateless: 'stateless',
  unknown: 'unknown',
} as const;

export const PersonsCountriesListGender = {
  F: 'F',
  M: 'M',
  O: 'O',
  U: 'U',
} as const;

export const PersonsCountriesListMedicalStatus = {
  critical: 'critical',
  deceased: 'deceased',
  health_concerns: 'health_concerns',
  healthy: 'healthy',
  unknown: 'unknown',
} as const;

export const PersonsCountriesListQualityTier = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const PersonsWatchdogListCurrentStatus = {
  deceased: 'deceased',
  detained: 'detained',
  disappeared: 'disappeared',
  released: 'released',
  restricted_movement: 'restricted_movement',
  rights_restricted: 'rights_restricted',
  stateless: 'stateless',
  unknown: 'unknown',
} as const;

export const PersonsWatchdogListGender = {
  F: 'F',
  M: 'M',
  O: 'O',
  U: 'U',
} as const;

export const PersonsWatchdogListMedicalStatus = {
  critical: 'critical',
  deceased: 'deceased',
  health_concerns: 'health_concerns',
  healthy: 'healthy',
  unknown: 'unknown',
} as const;

export const PersonsWatchdogListQualityTier = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const RelationshipsListRelationshipType = {
  child: 'child',
  other: 'other',
  parent: 'parent',
  sibling: 'sibling',
  spouse: 'spouse',
} as const;

export const ReportsListSourceType = {
  document: 'document',
  firsthand: 'firsthand',
  news: 'news',
  secondhand: 'secondhand',
} as const;

export const PatchedPersonWriteRequestGender = {...GenderEnum,...BlankEnum,} as const

export const PersonDetailGender = {...GenderEnum,...BlankEnum,} as const

export const PersonListGender = {...GenderEnum,...BlankEnum,} as const

export const PersonWriteGender = {...GenderEnum,...BlankEnum,} as const

export const PersonWriteRequestGender = {...GenderEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonDetailQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonListQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonWriteQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonWriteRequestQualityTier = {...QualityTierEnum,...NullEnum,} as const

/**
 * Generated by orval v7.21.0 🍺
 * Do not edit manually.
 * Testimonies.world API
 * Casework platform for documenting human rights cases. Sensitive endpoints (contacts, sensitive media) require authentication.
 * OpenAPI spec version: 1.0.0
 */
/**
 * * `outreach` - Outreach
* `legal_filing` - Legal filing
* `media` - Media engagement
* `advocacy` - Advocacy
* `investigation` - Investigation
* `other` - Other
 */
export type ActionTypeEnum = typeof ActionTypeEnum[keyof typeof ActionTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type BlankEnum = typeof BlankEnum[keyof typeof BlankEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface CaseCategory {
  readonly id: number;
  /** @maxLength 100 */
  name: string;
  description?: string;
}

export type CaseworkRecordSeenByItem = {[key: string]: string};

export interface CaseworkRecord {
  readonly id: number;
  readonly performed_by_name: string;
  readonly seen_by: readonly CaseworkRecordSeenByItem[];
  action_type?: ActionTypeEnum;
  description: string;
  date: string;
  status?: StatusEnum;
  next_steps?: string;
  notes?: string;
  readonly created_at: string;
  readonly updated_at: string;
  /** @nullable */
  readonly performed_by: number | null;
  persons?: number[];
}

export interface CaseworkRecordRequest {
  action_type?: ActionTypeEnum;
  /** @minLength 1 */
  description: string;
  date: string;
  status?: StatusEnum;
  next_steps?: string;
  notes?: string;
  persons?: number[];
}

export interface CategoryCount {
  name: string;
  count: number;
}

export interface Contact {
  readonly id: number;
  /** @maxLength 255 */
  name: string;
  role?: RoleEnum;
  /** @maxLength 50 */
  phone?: string;
  /** @maxLength 254 */
  email?: string;
  /** @maxLength 50 */
  signal?: string;
  /** @maxLength 50 */
  whatsapp?: string;
  notes?: string;
  readonly created_at: string;
  /** @nullable */
  readonly deleted_at: string | null;
  persons?: number[];
}

export interface ContactRequest {
  /**
   * @minLength 1
   * @maxLength 255
   */
  name: string;
  role?: RoleEnum;
  /** @maxLength 50 */
  phone?: string;
  /** @maxLength 254 */
  email?: string;
  /** @maxLength 50 */
  signal?: string;
  /** @maxLength 50 */
  whatsapp?: string;
  notes?: string;
  persons?: number[];
}

export interface CountryCountEntry {
  country: string;
  count: number;
}

/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
 */
export type CurrentStatusEnum = typeof CurrentStatusEnum[keyof typeof CurrentStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Family-relationship CRUD payload.

Read shape: full row plus denormalised `person_a_name` /
`person_b_name` so the frontend can render the list without
resolving FK IDs separately.

Write shape: accepts `person_a` and `person_b` as FK IDs (DRF
`PrimaryKeyRelatedField` is the default for `IntegerField`-with-FK
in `ModelSerializer`).

Validation (see `validate`):
    - `person_a != person_b` — no self-link.
    - One row per ordered `(person_a, person_b)` pair, regardless
      of type — the model already enforces this via
      `unique_together = ['person_a', 'person_b']` but we drop
      DRF's auto-validator (see `get_unique_together_validators`)
      so the volunteer sees a friendlier message.
    - For undirected types (`sibling`, `spouse`, `other`), the
      reverse-ordered pair is also rejected. `parent` / `child`
      allow either direction (direction carries meaning).
 */
export interface FamilyRelationship {
  readonly id: number;
  person_a: number;
  person_b: number;
  readonly person_a_name: string;
  readonly person_b_name: string;
  relationship_type: RelationshipTypeEnum;
  /** @maxLength 255 */
  notes?: string;
}

/**
 * Family-relationship CRUD payload.

Read shape: full row plus denormalised `person_a_name` /
`person_b_name` so the frontend can render the list without
resolving FK IDs separately.

Write shape: accepts `person_a` and `person_b` as FK IDs (DRF
`PrimaryKeyRelatedField` is the default for `IntegerField`-with-FK
in `ModelSerializer`).

Validation (see `validate`):
    - `person_a != person_b` — no self-link.
    - One row per ordered `(person_a, person_b)` pair, regardless
      of type — the model already enforces this via
      `unique_together = ['person_a', 'person_b']` but we drop
      DRF's auto-validator (see `get_unique_together_validators`)
      so the volunteer sees a friendlier message.
    - For undirected types (`sibling`, `spouse`, `other`), the
      reverse-ordered pair is also rejected. `parent` / `child`
      allow either direction (direction carries meaning).
 */
export interface FamilyRelationshipRequest {
  person_a: number;
  person_b: number;
  relationship_type: RelationshipTypeEnum;
  /** @maxLength 255 */
  notes?: string;
}

/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
export type GenderEnum = typeof GenderEnum[keyof typeof GenderEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `record_created` - New casework record
* `record_updated` - Casework record updated
* `status_done` - Casework marked done
* `record_seen` - A peer opened this record
 */
export type KindEnum = typeof KindEnum[keyof typeof KindEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface MarkAllReadResponse {
  updated: number;
}

export interface Media {
  readonly id: number;
  /**
   * @nullable
   * @pattern (?:jpg|jpeg|png|gif|webp|heic|tiff|bmp|pdf|mp4|mov|webm)$
   */
  file?: string | null;
  /** @maxLength 1000 */
  url?: string;
  media_type?: MediaTypeEnum;
  visibility?: VisibilityEnum;
  /** @maxLength 500 */
  description?: string;
  readonly created_at: string;
  /** @nullable */
  person?: number | null;
  /** @nullable */
  report?: number | null;
  /** @nullable */
  readonly uploaded_by: number | null;
}

export interface MediaRequest {
  /**
   * @nullable
   * @pattern (?:jpg|jpeg|png|gif|webp|heic|tiff|bmp|pdf|mp4|mov|webm)$
   */
  file?: Blob | null;
  /** @maxLength 1000 */
  url?: string;
  media_type?: MediaTypeEnum;
  visibility?: VisibilityEnum;
  /** @maxLength 500 */
  description?: string;
  /** @nullable */
  person?: number | null;
  /** @nullable */
  report?: number | null;
}

/**
 * * `photo` - Photo
* `document` - Document
* `video` - Video
* `link` - External link
 */
export type MediaTypeEnum = typeof MediaTypeEnum[keyof typeof MediaTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
export type MedicalStatusEnum = typeof MedicalStatusEnum[keyof typeof MedicalStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface Notification {
  readonly id: number;
  readonly kind: KindEnum;
  /** @nullable */
  readonly casework: number | null;
  /**
   * The user whose action caused this notification (often ≠ recipient).
   * @nullable
   */
  readonly actor: number | null;
  readonly actor_name: string;
  readonly casework_action_type: string;
  readonly casework_persons: readonly string[];
  readonly is_read: boolean;
  /** @nullable */
  readonly read_at: string | null;
  readonly created_at: string;
}

export type NullEnum = typeof NullEnum[keyof typeof NullEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface PaginatedCaseCategoryList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: CaseCategory[];
}

export interface PaginatedCaseworkRecordList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: CaseworkRecord[];
}

export interface PaginatedContactList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Contact[];
}

export interface PaginatedCountryCountEntryList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: CountryCountEntry[];
}

export interface PaginatedFamilyRelationshipList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: FamilyRelationship[];
}

export interface PaginatedMediaList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Media[];
}

export interface PaginatedNotificationList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Notification[];
}

export interface PaginatedPersonListList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: PersonList[];
}

export interface PaginatedReportList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Report[];
}

export interface PaginatedUserPreferenceList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: UserPreference[];
}

export interface PatchedCaseworkRecordRequest {
  action_type?: ActionTypeEnum;
  /** @minLength 1 */
  description?: string;
  date?: string;
  status?: StatusEnum;
  next_steps?: string;
  notes?: string;
  persons?: number[];
}

export interface PatchedContactRequest {
  /**
   * @minLength 1
   * @maxLength 255
   */
  name?: string;
  role?: RoleEnum;
  /** @maxLength 50 */
  phone?: string;
  /** @maxLength 254 */
  email?: string;
  /** @maxLength 50 */
  signal?: string;
  /** @maxLength 50 */
  whatsapp?: string;
  notes?: string;
  persons?: number[];
}

/**
 * Family-relationship CRUD payload.

Read shape: full row plus denormalised `person_a_name` /
`person_b_name` so the frontend can render the list without
resolving FK IDs separately.

Write shape: accepts `person_a` and `person_b` as FK IDs (DRF
`PrimaryKeyRelatedField` is the default for `IntegerField`-with-FK
in `ModelSerializer`).

Validation (see `validate`):
    - `person_a != person_b` — no self-link.
    - One row per ordered `(person_a, person_b)` pair, regardless
      of type — the model already enforces this via
      `unique_together = ['person_a', 'person_b']` but we drop
      DRF's auto-validator (see `get_unique_together_validators`)
      so the volunteer sees a friendlier message.
    - For undirected types (`sibling`, `spouse`, `other`), the
      reverse-ordered pair is also rejected. `parent` / `child`
      allow either direction (direction carries meaning).
 */
export interface PatchedFamilyRelationshipRequest {
  person_a?: number;
  person_b?: number;
  relationship_type?: RelationshipTypeEnum;
  /** @maxLength 255 */
  notes?: string;
}

export interface PatchedMediaRequest {
  /**
   * @nullable
   * @pattern (?:jpg|jpeg|png|gif|webp|heic|tiff|bmp|pdf|mp4|mov|webm)$
   */
  file?: Blob | null;
  /** @maxLength 1000 */
  url?: string;
  media_type?: MediaTypeEnum;
  visibility?: VisibilityEnum;
  /** @maxLength 500 */
  description?: string;
  /** @nullable */
  person?: number | null;
  /** @nullable */
  report?: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -2147483648
 * @maximum 2147483647
 * @nullable
 */
export type PatchedPersonWriteRequestQualityTier = typeof PatchedPersonWriteRequestQualityTier[keyof typeof PatchedPersonWriteRequestQualityTier]  | null;

/**
 * Serializer for creating/updating persons.
 */
export interface PatchedPersonWriteRequest {
  category_ids?: number[];
  /**
   * @minLength 1
   * @maxLength 255
   */
  name?: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /**
   * @minLength 1
   * @maxLength 100
   */
  country?: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PatchedPersonWriteRequestGender[keyof typeof PatchedPersonWriteRequestGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: Blob | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   * @nullable
   */
  quality_tier?: PatchedPersonWriteRequestQualityTier;
  is_published?: boolean;
}

export interface PatchedReportRequest {
  source_type?: SourceTypeEnum;
  /**
   * Public attribution — e.g. "family member", "BBC report"
   * @maxLength 500
   */
  source_attribution?: string;
  /** @maxLength 255 */
  reporter_name?: string;
  reporter_contact?: string;
  /** @nullable */
  date_start?: string | null;
  /**
   * Leave blank for single-date events
   * @nullable
   */
  date_end?: string | null;
  /** @maxLength 255 */
  rough_location?: string;
  /** @maxLength 500 */
  precise_location?: string;
  /** @minLength 1 */
  narrative?: string;
  /** What family/source believes is the reason */
  suspected_reason?: string;
  /** What the state officially charged */
  official_reason?: string;
  /** If true, entire report hidden from public view */
  is_private?: boolean;
  person?: number;
}

export interface PatchedUserPreferenceRequest {
  /** Receive an email when casework events affect you. */
  notify_email?: boolean;
  /** Show in-app notifications in the bell. */
  notify_inapp?: boolean;
}

export type PersonDetailFamilyItem = {[key: string]: unknown};

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -2147483648
 * @maximum 2147483647
 * @nullable
 */
export type PersonDetailQualityTier = typeof PersonDetailQualityTier[keyof typeof PersonDetailQualityTier]  | null;

/**
 * Full serializer with reports and media for detail views.
 */
export interface PersonDetail {
  readonly id: number;
  readonly categories: readonly CaseCategory[];
  readonly reports: readonly Report[];
  readonly media_files: readonly Media[];
  readonly days_since_last_report: number;
  readonly family: readonly PersonDetailFamilyItem[];
  /** @nullable */
  readonly profile_image_url: string | null;
  /** @maxLength 255 */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /** @maxLength 100 */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonDetailGender[keyof typeof PersonDetailGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: string | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   * @nullable
   */
  quality_tier?: PersonDetailQualityTier;
  is_published?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  /** @nullable */
  readonly created_by: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -2147483648
 * @maximum 2147483647
 * @nullable
 */
export type PersonListQualityTier = typeof PersonListQualityTier[keyof typeof PersonListQualityTier]  | null;

/**
 * Lightweight serializer for list views.
 */
export interface PersonList {
  readonly id: number;
  readonly categories: readonly CaseCategory[];
  readonly report_count: number;
  readonly days_since_last_report: number;
  /** @nullable */
  readonly profile_image_url: string | null;
  /** @maxLength 255 */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /** @maxLength 100 */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonListGender[keyof typeof PersonListGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: string | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   * @nullable
   */
  quality_tier?: PersonListQualityTier;
  is_published?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  /** @nullable */
  readonly created_by: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -2147483648
 * @maximum 2147483647
 * @nullable
 */
export type PersonWriteQualityTier = typeof PersonWriteQualityTier[keyof typeof PersonWriteQualityTier]  | null;

/**
 * Serializer for creating/updating persons.
 */
export interface PersonWrite {
  readonly id: number;
  category_ids?: number[];
  /** @maxLength 255 */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /** @maxLength 100 */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonWriteGender[keyof typeof PersonWriteGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: string | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   * @nullable
   */
  quality_tier?: PersonWriteQualityTier;
  is_published?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  /** @nullable */
  readonly created_by: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -2147483648
 * @maximum 2147483647
 * @nullable
 */
export type PersonWriteRequestQualityTier = typeof PersonWriteRequestQualityTier[keyof typeof PersonWriteRequestQualityTier]  | null;

/**
 * Serializer for creating/updating persons.
 */
export interface PersonWriteRequest {
  category_ids?: number[];
  /**
   * @minLength 1
   * @maxLength 255
   */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /**
   * @minLength 1
   * @maxLength 100
   */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonWriteRequestGender[keyof typeof PersonWriteRequestGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: Blob | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   * @nullable
   */
  quality_tier?: PersonWriteRequestQualityTier;
  is_published?: boolean;
}

/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 */
export type QualityTierEnum = typeof QualityTierEnum[keyof typeof QualityTierEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `parent` - Parent
* `child` - Child
* `sibling` - Sibling
* `spouse` - Spouse
* `other` - Other relative
 */
export type RelationshipTypeEnum = typeof RelationshipTypeEnum[keyof typeof RelationshipTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface Report {
  readonly id: number;
  readonly media_files: readonly Media[];
  source_type?: SourceTypeEnum;
  /**
   * Public attribution — e.g. "family member", "BBC report"
   * @maxLength 500
   */
  source_attribution?: string;
  /** @maxLength 255 */
  reporter_name?: string;
  reporter_contact?: string;
  /** @nullable */
  date_start?: string | null;
  /**
   * Leave blank for single-date events
   * @nullable
   */
  date_end?: string | null;
  /** @maxLength 255 */
  rough_location?: string;
  /** @maxLength 500 */
  precise_location?: string;
  narrative: string;
  /** What family/source believes is the reason */
  suspected_reason?: string;
  /** What the state officially charged */
  official_reason?: string;
  /** If true, entire report hidden from public view */
  is_private?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  person: number;
  /** @nullable */
  readonly created_by: number | null;
}

export interface ReportRequest {
  source_type?: SourceTypeEnum;
  /**
   * Public attribution — e.g. "family member", "BBC report"
   * @maxLength 500
   */
  source_attribution?: string;
  /** @maxLength 255 */
  reporter_name?: string;
  reporter_contact?: string;
  /** @nullable */
  date_start?: string | null;
  /**
   * Leave blank for single-date events
   * @nullable
   */
  date_end?: string | null;
  /** @maxLength 255 */
  rough_location?: string;
  /** @maxLength 500 */
  precise_location?: string;
  /** @minLength 1 */
  narrative: string;
  /** What family/source believes is the reason */
  suspected_reason?: string;
  /** What the state officially charged */
  official_reason?: string;
  /** If true, entire report hidden from public view */
  is_private?: boolean;
  person: number;
}

/**
 * * `family` - Family member
* `advocate` - Advocate
* `lawyer` - Lawyer
* `official` - Government official
* `journalist` - Journalist
* `reporter` - Reporter/witness
* `other` - Other
 */
export type RoleEnum = typeof RoleEnum[keyof typeof RoleEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `firsthand` - Firsthand
* `secondhand` - Secondhand
* `news` - News report
* `document` - Document
 */
export type SourceTypeEnum = typeof SourceTypeEnum[keyof typeof SourceTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface StatisticsCountryCount {
  country: string;
  count: number;
}

export type StatisticsResponseByStatus = {[key: string]: number};

export type StatisticsResponseByMedical = {[key: string]: number};

export interface StatisticsResponse {
  total: number;
  by_status: StatisticsResponseByStatus;
  by_country: StatisticsCountryCount[];
  by_category: CategoryCount[];
  by_medical: StatisticsResponseByMedical;
}

/**
 * * `open` - Open
* `in_progress` - In progress
* `done` - Done
 */
export type StatusEnum = typeof StatusEnum[keyof typeof StatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface UnreadCountResponse {
  count: number;
}

export interface UserPreference {
  /** Receive an email when casework events affect you. */
  notify_email?: boolean;
  /** Show in-app notifications in the bell. */
  notify_inapp?: boolean;
}

export interface UserPreferenceRequest {
  /** Receive an email when casework events affect you. */
  notify_email?: boolean;
  /** Show in-app notifications in the bell. */
  notify_inapp?: boolean;
}

/**
 * * `public` - Public
* `restricted` - Restricted — authenticated users only
* `sensitive` - Sensitive — advocates/admin only
 */
export type VisibilityEnum = typeof VisibilityEnum[keyof typeof VisibilityEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type CaseworkListParams = {
/**
 * * `outreach` - Outreach
* `legal_filing` - Legal filing
* `media` - Media engagement
* `advocacy` - Advocacy
* `investigation` - Investigation
* `other` - Other
 */
action_type?: CaseworkListActionType;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
performed_by?: number;
/**
 * A search term.
 */
search?: string;
/**
 * * `open` - Open
* `in_progress` - In progress
* `done` - Done
 */
status?: CaseworkListStatus;
};

export type CaseworkListActionType = typeof CaseworkListActionType[keyof typeof CaseworkListActionType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type CaseworkListStatus = typeof CaseworkListStatus[keyof typeof CaseworkListStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type CategoriesListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type ContactsListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * * `family` - Family member
* `advocate` - Advocate
* `lawyer` - Lawyer
* `official` - Government official
* `journalist` - Journalist
* `reporter` - Reporter/witness
* `other` - Other
 */
role?: ContactsListRole;
/**
 * A search term.
 */
search?: string;
};

export type ContactsListRole = typeof ContactsListRole[keyof typeof ContactsListRole];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type MediaListParams = {
/**
 * * `photo` - Photo
* `document` - Document
* `video` - Video
* `link` - External link
 */
media_type?: MediaListMediaType;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
person?: number;
report?: number;
/**
 * A search term.
 */
search?: string;
/**
 * * `public` - Public
* `restricted` - Restricted — authenticated users only
* `sensitive` - Sensitive — advocates/admin only
 */
visibility?: MediaListVisibility;
};

export type MediaListMediaType = typeof MediaListMediaType[keyof typeof MediaListMediaType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type MediaListVisibility = typeof MediaListVisibility[keyof typeof MediaListVisibility];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type NotificationsListParams = {
is_read?: boolean;
/**
 * * `record_created` - New casework record
* `record_updated` - Casework record updated
* `status_done` - Casework marked done
* `record_seen` - A peer opened this record
 */
kind?: NotificationsListKind;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type NotificationsListKind = typeof NotificationsListKind[keyof typeof NotificationsListKind];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListParams = {
category?: number[];
country?: string;
/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
 */
current_status?: PersonsListCurrentStatus;
/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
gender?: PersonsListGender;
is_published?: boolean;
/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
medical_status?: PersonsListMedicalStatus;
name?: string;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
quality?: number;
/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 * @nullable
 */
quality_tier?: PersonsListQualityTier;
/**
 * A search term.
 */
search?: string;
status?: string;
};

export type PersonsListCurrentStatus = typeof PersonsListCurrentStatus[keyof typeof PersonsListCurrentStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListGender = typeof PersonsListGender[keyof typeof PersonsListGender];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListMedicalStatus = typeof PersonsListMedicalStatus[keyof typeof PersonsListMedicalStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListQualityTier = typeof PersonsListQualityTier[keyof typeof PersonsListQualityTier] | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListParams = {
category?: number[];
country?: string;
/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
 */
current_status?: PersonsCountriesListCurrentStatus;
/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
gender?: PersonsCountriesListGender;
is_published?: boolean;
/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
medical_status?: PersonsCountriesListMedicalStatus;
name?: string;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
quality?: number;
/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 * @nullable
 */
quality_tier?: PersonsCountriesListQualityTier;
/**
 * A search term.
 */
search?: string;
status?: string;
};

export type PersonsCountriesListCurrentStatus = typeof PersonsCountriesListCurrentStatus[keyof typeof PersonsCountriesListCurrentStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListGender = typeof PersonsCountriesListGender[keyof typeof PersonsCountriesListGender];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListMedicalStatus = typeof PersonsCountriesListMedicalStatus[keyof typeof PersonsCountriesListMedicalStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListQualityTier = typeof PersonsCountriesListQualityTier[keyof typeof PersonsCountriesListQualityTier] | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListParams = {
category?: number[];
country?: string;
/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
 */
current_status?: PersonsWatchdogListCurrentStatus;
/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
gender?: PersonsWatchdogListGender;
is_published?: boolean;
/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
medical_status?: PersonsWatchdogListMedicalStatus;
name?: string;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
quality?: number;
/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 * @nullable
 */
quality_tier?: PersonsWatchdogListQualityTier;
/**
 * A search term.
 */
search?: string;
status?: string;
};

export type PersonsWatchdogListCurrentStatus = typeof PersonsWatchdogListCurrentStatus[keyof typeof PersonsWatchdogListCurrentStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListGender = typeof PersonsWatchdogListGender[keyof typeof PersonsWatchdogListGender];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListMedicalStatus = typeof PersonsWatchdogListMedicalStatus[keyof typeof PersonsWatchdogListMedicalStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListQualityTier = typeof PersonsWatchdogListQualityTier[keyof typeof PersonsWatchdogListQualityTier] | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PreferencesListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type RelationshipsListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
person?: number;
/**
 * * `parent` - Parent
* `child` - Child
* `sibling` - Sibling
* `spouse` - Spouse
* `other` - Other relative
 */
relationship_type?: RelationshipsListRelationshipType;
/**
 * A search term.
 */
search?: string;
};

export type RelationshipsListRelationshipType = typeof RelationshipsListRelationshipType[keyof typeof RelationshipsListRelationshipType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type ReportsListParams = {
date_from?: string;
date_to?: string;
is_private?: boolean;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
person?: number;
/**
 * A search term.
 */
search?: string;
/**
 * * `firsthand` - Firsthand
* `secondhand` - Secondhand
* `news` - News report
* `document` - Document
 */
source_type?: ReportsListSourceType;
};

export type ReportsListSourceType = typeof ReportsListSourceType[keyof typeof ReportsListSourceType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

