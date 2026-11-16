Prepare one release of a web service. The work includes a cache fix with an existing failing test, an export endpoint and SDK update, webhook security, and a live data migration with rollback preparation.

1. Fix the cache bug; a failing test exists.
2. Decide the new field of the export endpoint.
3. Implement the endpoint to the contract, with tests.
4. Update the client SDK types to the contract.
5. Verify webhook signatures and reject replays.
6. Review row 5 with test output.
7. Write the data migration with dry run and rollback.
8. Run the migration on the live data.
9. Verify the data after the migration.
10. Review rows 1, 3, 4 and 7 for the final change.

keep the step numbers; do not merge or split steps
