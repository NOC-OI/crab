# CRAB Compatible Data

CRAB accepts arbitrary data as parquet files.

## Data files

Raw orthogonal data, and metadata from the original instrument.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_DATA_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| dimensions | uint64, number of dimensions each entry contains |
| domain_types | JSON encoded array, stating the type of each domain. Usual domain types are: "spatial", "chromatic", "temporal", "frequency", "feature" |
| domains | Array of uint8, each uint8 referring to a domain type |
| bit_depth | uint64, the bit depth of the data |
| stored_bit_depth | uint64, how many bits per value. This MAY be different from bit_depth, for example 7-bit ADC data MAY be stored as the least significant of 8-bits to allow for byte-aligned arrays. |
| contains_udts | Concatenated binary string of binary UDTs |

**Example for an image system:**

| Key | Value |
| --- | --- |
| data_type | CRAB_DATA_V1 |
| last_modified | 1762184335 |
| dimensions | 3 |
| domain_types | \["spatial", "chromatic"\] |
| domains | 0, 0, 1 |
| bit_depth | 8 |
| stored_bit_depth | 8 |
| contains_udts | 0x022dc621accf3dc224a43f022373c200006839044c |

#### Note about domain types

While it may seem abstract, each domain type has a specific function to allow definition of arbitrary orthagonal data.

Spatial dimensions might be the most obvious type. Each different spatial dimention represents a new spatial axis that a data point might refer to.

Temporal dimensions are another common type, that is largely self explanatory. It generally only makes sense to have one such dimension, and many annotation suites will be unable to process any more than the first temporal dimension.

A feature dimension is a dimension which represents a change in type of data. One example for use of such data might be in water monitoring, for separating the different features of salinity, temperature and turbidity. In this case there would be a "feature" dimension of extent 3.

Chromatic and frequency dimensions are a special case of feature dimensions, and CRAB will treat them identically. They are used for colour channels in images and frequency bins in spectrogram data respectively.

### Per-entry values

| Key | Expected value |
| --- | --- |
| udt | Full UDT |
| udt_bin | Binary compact UDT, for search |
| data | Raw binary data, column major |
| last_modified | uint64, Unix timestamp of data collection |
| extents | Array of uint64, one for each dimension |

**Example for an image system:**

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| data | \<raw data\> |
| extents | 400, 600, 3 |

## Region of interest

Each ROI simply maps out the extents of an observation. This is often an automatic process, and may be abstracted into higher dimensions. Each ROI has a UUID assigned to ensure change tracking can be carried out effectively. A ROI might be seen as a type of annotation, but it is often useful to seperate it from the process of identification and classification.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_ROI_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| references_udts | Concatenated binary string of binary compact UDTs referenced |
| software_map | JSON encoded array of strings, URIs (preferably DOIs) of the softwares used to create the annotation set |

**Example for annotations from EcoTaxa**

| Key | Value |
| --- | --- |
| data_type | CRAB_ROI_V1 |
| last_modified | 1762184646 |
| references_udts | 0x022dc621accf3dc224a43f022373c200006839044c |

### Per-entry values

| Key | Expected value |
| --- | --- |
| udt | Full UDT |
| udt_bin | Binary compact UDT, for search |
| uuid | In compact binary form, used as the unique identifier of the ROI |
| last_modified | uint64, Unix timestamp of ROI modification time |
| extents | Array of uint64, **two** for each dimension, first an lower bound, then an upper bound |
| annotator | String, an email address or ORCID identifier (MUST be formatted with dashes). MUST be null if no human involvement |
| annotation_software | String, URI reference to the software used to create the ROI |

**Note regarding use_dictionary:** It is highly reccomended to use the "use_dictionary" parameter for "annotator" and "annotation_software".

**Example for annotations from EcoTaxa**

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| uuid | 0x486b38eefc0a4a1aa16a1ac3b0eb5ed8 |
| last_modified | 1762184586 |
| extents | 0, 400, 0, 600, 0, 3 |
| annotator | null |
| annotation_software | https://github.com/NOC-OI/ifcbproc |


## Annotation files

Each annotation is attached to a specific ROI, of a specific data frame. In a biological context, the most important metadata tag is usually "taxa", which should contain taxanomic information relative to the chosen authoratative taxonomy. Other metadata might be stored in an annotation however, such as particle size or other morphological measurements.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_ANNOTATION_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| references_udts | Concatenated binary string of binary compact UDTs referenced |

**Example for annotations from EcoTaxa**

| Key | Value |
| --- | --- |
| data_type | CRAB_ANNOTATION_V1 |
| last_modified | 1762184646 |
| references_udts | 0x022dc621accf3dc224a43f022373c200006839044c |

### Per-entry values

| Key | Expected value |
| --- | --- |
| udt | Full UDT |
| udt_bin | Binary compact UDT, for search |
| uuid | In compact binary form, used as the unique identifier of the ROI referenced |
| last_modified | uint64, Unix timestamp of annotation modification time |
| annotator | String, an email address or ORCID identifier (MUST be formatted with dashes). MUST be null if no human involvement |
| annotation_software | uint64, cross reference to the software used to create the annotation |
| field_\<field_name\> | Arbitrary fields for use in annotation, common ones listed below |

**Common fields***

- taxa_id (e.g. 8211946)
- taxonomy (e.g. https://www.gbif.org/)

**Note regarding use_dictionary:** It is highly reccomended to use the "use_dictionary" parameter for "annotator", "annotation_software" and any other string field with high repitition.

**Example for annotations from EcoTaxa**

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| uuid | 0x486b38eefc0a4a1aa16a1ac3b0eb5ed8 |
| last_modified | 1762184586 |
| annotator | null |
| annotation_software | 0 |
