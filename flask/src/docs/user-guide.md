# CRAB User Guide

## Uploading data

Use a processing tool that generates [CRAB compatible data](compatible-data.md). This will usually generate at least two files, your "deposit", a zip file containing all original data files, and a "data.parquet" file containing all raw data. Some instruments generate locality data, or primarily work with ROIs. In this case you will likely also have a "annotation.parquet" file, which contains ROI information and possibly extra metadata.

## Building a project

CRAB organises most data into projects. Think of a project as a self-contained collection of data that all relates to a particular study. Each project can have several collections, with each collection being a different variation of the data. Many projects will only consist of the default "main" collection. Snapshots represent a collection at a particular point of time. Analagous to a research output, these snapshots hold all data and metadata frozen in time. CRAB export utilities are built around snapshots to support replicability. Someone else using your code, and your exact snapshot, should be able to replicate your findings and results.

## Exporting data

CRAB presents many different ways to access your data. A common use case is exporting datasets to machine learning libraries such as [Keras](https://keras.io/). To support this use case, CRAB generates [Croissant files](https://docs.mlcommons.org/croissant/) which can be accessed from a project's page after a snapshot has been taken.
