/**
 * ts-to-zod configuration.
 *
 * @type {import("ts-to-zod").TsToZodConfig}
 */
module.exports = [
  {
    name: 'api',
    input: 'src/api/types.ts',
    output: 'src/api/schemas.ts',
  },
];
