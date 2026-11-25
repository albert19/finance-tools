<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'monthly_budgets')]
#[ORM\UniqueConstraint(name: 'uniq_period', columns: ['user_id', 'year', 'month'])]
class MonthlyBudget
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\ManyToOne(targetEntity: User::class), ORM\JoinColumn(name: 'user_id', nullable: false, onDelete: 'CASCADE')]
    public User $owner;
    #[ORM\Column(type: 'smallint')]
    public int $year;
    // Keep integer hydration for months 1-12; DBAL introspects MySQL TINYINT as boolean.
    #[ORM\Column(type: 'smallint', columnDefinition: 'TINYINT NOT NULL')]
    public int $month;
    #[ORM\Column(type: 'text', length: 65535)]
    public string $notes;
    // Existing optimistic version is updated atomically with DBAL's compare-and-swap.
    #[ORM\Column(type: 'integer', options: ['default' => 1])]
    public int $version = 1;
}
